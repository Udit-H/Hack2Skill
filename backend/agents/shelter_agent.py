import os
import re
import jinja2
import logging

from models.session import SessionState, AgentResponse, AgentActionType, AgentType
from models.shelter import ShelterAgentState, ShelterWorkflowStatus
from services.llm_service import LLMService
from services.shelter_service import ShelterService

# ── Simple geocoding for Bengaluru areas (hackathon-grade) ──────────
BENGALURU_AREAS = {
    "indiranagar":   (12.9716, 77.6412),
    "koramangala":   (12.9352, 77.6245),
    "hsr layout":    (12.9116, 77.6389),
    "hsr":           (12.9116, 77.6389),
    "whitefield":    (12.9698, 77.7500),
    "electronic city":(12.8390, 77.6780),
    "jayanagar":     (12.9250, 77.5938),
    "jp nagar":      (12.9063, 77.5857),
    "malleshwaram":  (12.9965, 77.5713),
    "rajajinagar":   (12.9880, 77.5530),
    "yelahanka":     (13.1007, 77.5963),
    "hebbal":        (13.0350, 77.5970),
    "marathahalli":  (12.9591, 77.7014),
    "sarjapur":      (12.8580, 77.7870),
    "btm layout":    (12.9166, 77.6101),
    "btm":           (12.9166, 77.6101),
    "banashankari":  (12.9255, 77.5468),
    "basavanagudi":  (12.9430, 77.5745),
    "mg road":       (12.9756, 77.6066),
    "majestic":      (12.9767, 77.5713),
    "yemlur":        (12.9569, 77.6690),
    "ulsoor":        (12.9810, 77.6230),
    "shivajinagar":  (12.9857, 77.6057),
    "richmond town": (12.9620, 77.5980),
    "frazer town":   (12.9980, 77.6140),
    "rt nagar":      (13.0210, 77.5970),
    "vijayanagar":   (12.9710, 77.5330),
    "nagarbhavi":    (12.9600, 77.5100),
    "kengeri":       (12.9050, 77.4830),
    "bengaluru":     (12.9716, 77.5946),
    "bangalore":     (12.9716, 77.5946),
}

def _parse_raw_coordinates(text: str) -> dict | None:
    """Extract lat,lng from text like '12.9716, 77.6412' or 'my location is 12.9716,77.6412'."""
    if not text:
        return None
    match = re.search(r'(-?\d{1,3}\.\d{3,})\s*[,\s]\s*(-?\d{1,3}\.\d{3,})', text)
    if match:
        lat, lng = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            logging.info(f"[GEOCODE] Parsed raw coordinates: ({lat}, {lng})")
            return {"lat": lat, "lng": lng}
    return None

def _geocode_location(location_text: str) -> dict | None:
    """Best-effort geocoding from location text to coordinates."""
    if not location_text:
        return None
    text = location_text.lower().strip()
    for area, (lat, lng) in BENGALURU_AREAS.items():
        if area in text:
            logging.info(f"[GEOCODE] Matched '{area}' → ({lat}, {lng})")
            return {"lat": lat, "lng": lng}
    # Try raw coordinate parsing (e.g. "12.9716,77.6412")
    raw = _parse_raw_coordinates(text)
    if raw:
        return raw
    # Fallback: central Bengaluru
    if any(city in text for city in ["bengaluru", "bangalore", "blr"]):
        return {"lat": 12.9716, "lng": 77.5946}
    return None

def _match_shelter_selection(user_message: str, shelters: list) -> int | None:
    """Try to match the user's selection to a shelter. Returns shelter_id or None."""
    if not user_message or not shelters:
        return None
    msg = user_message.lower().strip()
    
    # Match by number: "1", "number 1", "#1", "the first one", "option 1"
    ordinals = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
    num_match = re.search(r'(?:number|#|option)?\s*(\d)', msg)
    if num_match:
        idx = int(num_match.group(1)) - 1  # 0-based
        if 0 <= idx < len(shelters):
            return shelters[idx].shelter_id
    for word, idx in ordinals.items():
        if word in msg and idx <= len(shelters):
            return shelters[idx - 1].shelter_id
    
    # Match by name (fuzzy substring)
    for s in shelters:
        name_lower = s.name.lower()
        # Check if any significant part of the shelter name appears in user message
        name_words = [w for w in name_lower.split() if len(w) > 3]
        matches = sum(1 for w in name_words if w in msg)
        if matches >= 2 or name_lower in msg:
            return s.shelter_id
    
    return None


def _is_consent_message(user_message: str) -> bool:
    """Check if the user is granting consent."""
    if not user_message:
        return False
    msg = user_message.lower().strip()
    consent_phrases = ["yes", "yeah", "yep", "sure", "go ahead", "ok", "okay", 
                       "please", "i agree", "that's fine", "do it", "confirm", "approved"]
    return any(phrase in msg for phrase in consent_phrases)


class ShelterAgent:
    def __init__(self):
        self.llm = LLMService()
        self.db_service = ShelterService()
        
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))

    async def get_shelter_system_prompt(self, triage_state, current_state: ShelterAgentState, memory_context: str, db_attempted: bool) -> str:
        template = self.template_env.get_template("shelter_agent_system.j2")        
        state_json = current_state.model_dump_json(exclude={"matched_shelters"})
        
        return template.render(
            triage_category=triage_state.category.value if triage_state.category else "Unknown",
            incident_summary=triage_state.incident_summary,
            db_shelters=[s.model_dump() for s in current_state.matched_shelters] if current_state.matched_shelters else[],
            db_attempted=db_attempted,
            current_state_json=state_json,
            memory_context=memory_context
        )

    async def process_turn(self, session: SessionState, memory_manager, user_message: str = None) -> AgentResponse:
        triage = session.triage
        
        # Initialize Shelter state if it doesn't exist yet
        if not session.shelter:
            session.shelter = ShelterAgentState()
        current_state = session.shelter

        user_wants_more = any(phrase in user_message.lower() for phrase in [
            "others", "other", "more options", "different", "else", "another"
        ]) if user_message else False
        
        if user_wants_more and current_state.matched_shelters:
            print("[SYSTEM]: User wants different options. Expanding search radius...")
            
            lat = current_state.user_coordinates.get('lat', 12.9803) if current_state.user_coordinates else 12.9803
            lng = current_state.user_coordinates.get('lng', 77.5688) if current_state.user_coordinates else 77.5688
            
            try:
                shelters = await self.db_service.find_all_shelters(lat=lat, lng=lng, radius_km=25)
            except Exception as e:
                logging.error(f"[SHELTER] Expanded search failed: {e}")
                shelters = []
            
            if shelters:
                # Filter out already shown shelters
                shown_ids = [s.shelter_id for s in current_state.matched_shelters]
                new_shelters = [s for s in shelters if s.shelter_id not in shown_ids]
                
                if new_shelters:
                    current_state.matched_shelters = new_shelters[:5]
                    print(f"Found {len(new_shelters)} new options")
                else:
                    response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
                    response.reply_message = "I've shown you all available shelters in your area. Would you like me to contact any of the previously shown options, or would you prefer to share a different location?"
                    return response
            else:
                response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
                response.reply_message = "Unfortunately, I couldn't find any additional shelters in the expanded area. Would you like me to help you with the options I showed earlier?"
                return response
        
        
        # ── PRE-LOOP: Handle selection & consent in Python (LLM can't do this) ──
        if user_message and current_state.matched_shelters:
            # CASE A: Shelters shown, user hasn't selected yet → try to match selection
            if not current_state.selected_shelter_ids:
                selected_id = _match_shelter_selection(user_message, current_state.matched_shelters)
                if selected_id:
                    current_state.selected_shelter_ids = [selected_id]
                    current_state.workflow_status = ShelterWorkflowStatus.AWAITING_CONSENT
                    selected_shelter = next((s for s in current_state.matched_shelters if s.shelter_id == selected_id), None)
                    name = selected_shelter.name if selected_shelter else f"Shelter #{selected_id}"
                    session.shelter = current_state
                    response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
                    response.reply_message = f"Great choice — **{name}**. To reserve a spot, I'll need to share your name and basic details with the shelter manager. Do I have your permission to do this?"
                    return response
            
            # CASE B: User already selected, waiting for consent
            elif current_state.selected_shelter_ids and current_state.workflow_status == ShelterWorkflowStatus.AWAITING_CONSENT:
                if _is_consent_message(user_message):
                    current_state.user_consent_to_share = True
                    current_state.workflow_status = ShelterWorkflowStatus.COMPLETED
                    session.shelter = current_state
                    selected_shelter = next((s for s in current_state.matched_shelters if s.shelter_id == current_state.selected_shelter_ids[0]), None)
                    response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
                    if selected_shelter:
                        response.reply_message = (
                            f"I've shared your details with **{selected_shelter.name}**. "
                            f"They will be expecting you.\n\n"
                            f"📍 Address: {selected_shelter.address}\n"
                            f"📞 Phone: {selected_shelter.contact_number or 'N/A'}\n"
                            f"🗺️ Directions: {selected_shelter.google_maps_url}\n\n"
                            f"Please head there as soon as possible. Stay safe."
                        )
                    else:
                        response.reply_message = "I've shared your details with the shelter manager. They will be expecting you. Stay safe."
                    response.action_type = AgentActionType.SWITCH_AGENT
                    response.next_active_agent = AgentType.ORCHESTRATOR
                    return response
                else:
                    # User declined or said something else
                    current_state.selected_shelter_ids = []
                    current_state.workflow_status = ShelterWorkflowStatus.AWAITING_SELECTION
                    session.shelter = current_state
                    response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
                    response.reply_message = "No problem at all. Would you like to choose a different shelter from the list, or should I search for more options?"
                    return response
        
        # --- THE REACT LOOP (CRITICAL FOR DYNAMIC PREFERENCES) ---
        max_loops = 3
        loop_count = 0
        db_query_attempted = False
        
        # ── Pre-loop: extract raw GPS coordinates from user message ──
        if user_message:
            raw_coords = _parse_raw_coordinates(user_message)
            if raw_coords:
                current_state.user_coordinates = raw_coords
                if not current_state.user_location_text:
                    current_state.user_location_text = f"{raw_coords['lat']},{raw_coords['lng']}"
                logging.info(f"[SHELTER] Extracted GPS from user message → {raw_coords}")
        
        while loop_count < max_loops:
            loop_count += 1
            
            # 0. AUTO-GEOCODE: If we have location text but no coordinates, geocode now
            if current_state.user_location_text and not current_state.user_coordinates:
                coords = _geocode_location(current_state.user_location_text)
                if coords:
                    current_state.user_coordinates = coords
                    logging.info(f"[SHELTER] Auto-geocoded '{current_state.user_location_text}' → {coords}")
            
            # 1. DB RETRIEVAL PHASE — trigger if we have coords + prefs and no shelters yet
            needs_db_search = (
                current_state.user_coordinates 
                and current_state.user_preferences 
                and not current_state.matched_shelters
            )
            if needs_db_search:
                db_query_attempted = True    
                
                # Default Bengaluru Coordinates
                lat = current_state.user_coordinates.get('lat', 12.9803) 
                lng = current_state.user_coordinates.get('lng', 77.5688)
                
                try:
                    shelters = await self.db_service.find_appropriate_shelters(
                        lat=lat, lng=lng, 
                        crisis_category=triage.category, 
                        preferences=current_state.user_preferences
                    )
                    current_state.matched_shelters = shelters
                    print(f"[DB RESULT]: {len(shelters) if shelters else 0} shelters found")
                except Exception as e:
                    logging.error(f"[SHELTER] DB search failed: {e}")
                    current_state.matched_shelters = []
                    print(f"[DB ERROR]: {e} — will ask user to try again")

            # 2. PROMPT GENERATION
            memory_context = memory_manager.get_memory_context()
            system_prompt = await self.get_shelter_system_prompt(
                triage, current_state, memory_context, db_query_attempted
            )

            # 3. LLM EVALUATION
            updated_state: ShelterAgentState = await self.llm.create_structured(
                response_model=ShelterAgentState,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message or "Evaluate the current state and dictate the next step."}
                ]
            )

            print(f"[LLM STATUS]: {updated_state.workflow_status.value}")

            # ── STATE MERGE: The LLM returns a FULL new ShelterAgentState, but it
            #    cannot reliably manage complex/programmatic fields. Merge them back.
            # matched_shelters is ALWAYS managed by DB queries, never by LLM output.
            updated_state.matched_shelters = current_state.matched_shelters
            # Preserve any field the LLM may have accidentally nullified
            if current_state.user_coordinates and not updated_state.user_coordinates:
                updated_state.user_coordinates = current_state.user_coordinates
            if current_state.user_location_text and not updated_state.user_location_text:
                updated_state.user_location_text = current_state.user_location_text
            if current_state.user_preferences and not updated_state.user_preferences:
                updated_state.user_preferences = current_state.user_preferences

            # 4. INTERCEPT THE TRIGGER
            # Only honor trigger if we did NOT just run a DB search this iteration
            # (LLM set this flag before seeing the results — it's stale)
            if updated_state.trigger_new_db_search and not needs_db_search:
                updated_state.matched_shelters = []
                updated_state.trigger_new_db_search = False
                updated_state.selected_shelter_ids = []
                
                # Always re-geocode (location may have changed with new preferences)
                if updated_state.user_location_text:
                    coords = _geocode_location(updated_state.user_location_text)
                    if coords:
                        updated_state.user_coordinates = coords
                
                current_state = updated_state
                user_message = "[SYSTEM LOGIC]: Preferences changed. Database wiped. Triggering new DB search in loop."
                continue 
            
            # If no trigger, we break the loop and talk to the user.
            current_state = updated_state
            break

        # Save to global session memory
        session.shelter = current_state

        # --- PHASE 3: ORCHESTRATOR INSTRUCTIONS ---
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
        
        if current_state.workflow_status == ShelterWorkflowStatus.COMPLETED:
            response.reply_message = "I have confirmed your selection and sent your details to the shelter manager. Please proceed to the location using the map link provided."
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
        else:
            # Priority 1: If we found shelters and user hasn't selected → ALWAYS show them
            if current_state.matched_shelters and not current_state.selected_shelter_ids:
                lines = []
                for i, s in enumerate(current_state.matched_shelters[:5], 1):
                    dist = f" — {s.distance_km:.1f} km" if s.distance_km else ""
                    phone = f" | 📞 {s.contact_number}" if s.contact_number else ""
                    lines.append(f"  {i}. **{s.name}** ({s.shelter_type}){dist}\n     📍 {s.address}{phone}\n     🗺️ {s.google_maps_url}")
                shelter_lines = "\n".join(lines)
                response.reply_message = f"I found some shelters near you:\n\n{shelter_lines}\n\nWhich one feels safest for you?"
                current_state.workflow_status = ShelterWorkflowStatus.AWAITING_SELECTION
            # Priority 2: Use LLM's question
            elif current_state.next_question_for_user:
                response.reply_message = current_state.next_question_for_user
            # Priority 3: Fallback
            else:
                response.reply_message = "Could you please share your current location or the nearest area so I can search for shelters near you?"
            
        return response