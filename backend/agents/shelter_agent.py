import os
import jinja2
import instructor
from openai import AsyncOpenAI

from config.config import get_settings
from models.session import SessionState, AgentResponse, AgentActionType, AgentType
from models.shelter import ShelterAgentState, ShelterWorkflowStatus
from core.shelter_service import ShelterService

class ShelterAgent:
    def __init__(self):
        settings = get_settings()

        self.client = instructor.from_openai(AsyncOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url
        ), mode=instructor.Mode.JSON)

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
        current_state = session.shelter

        user_wants_more = any(phrase in user_message.lower() for phrase in [
            "others", "other", "more options", "different", "else", "another"
        ]) if user_message else False
        
        if user_wants_more and current_state.matched_shelters:
            print("[SYSTEM]: User wants different options. Expanding search radius...")
            
            lat = current_state.user_coordinates.get('lat', 12.9803) if current_state.user_coordinates else 12.9803
            lng = current_state.user_coordinates.get('lng', 77.5688) if current_state.user_coordinates else 77.5688
            
            shelters = await self.db_service.find_all_shelters(lat=lat, lng=lng, radius_km=25)
            
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
        
        
        # --- THE REACT LOOP (CRITICAL FOR DYNAMIC PREFERENCES) ---
        max_loops = 2
        loop_count = 0
        db_query_attempted = False
        
        while loop_count < max_loops:
            loop_count += 1
            
            # 1. DB RETRIEVAL PHASE
            if current_state.user_coordinates and current_state.user_preferences and not current_state.matched_shelters:
                db_query_attempted = True    
                
                # Default Bengaluru Coordinates
                lat = current_state.user_coordinates.get('lat', 12.9803) 
                lng = current_state.user_coordinates.get('lng', 77.5688)
                
                shelters = await self.db_service.find_appropriate_shelters(
                    lat=lat, lng=lng, 
                    crisis_category=triage.category, 
                    preferences=current_state.user_preferences
                )
                current_state.matched_shelters = shelters
                print(f"[DB RESULT]: {len(shelters) if shelters else 0} shelters found")

            # 2. PROMPT GENERATION
            memory_context = memory_manager.get_memory_context()
            system_prompt = await self.get_shelter_system_prompt(
                triage, current_state, memory_context, db_query_attempted
            )

            # 3. LLM EVALUATION
            updated_state: ShelterAgentState = await self.client.chat.completions.create(
                model="gemini-2.5-flash",
                response_model=ShelterAgentState,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message or "Evaluate the current state and dictate the next step."}
                ]
            )

            print(f"[LLM STATUS]: {updated_state.workflow_status.value}")

            # 4. INTERCEPT THE TRIGGER
            if updated_state.trigger_new_db_search:
                # The LLM realized it needs new data. We clear the old shelters, 
                # update the current_state, and LOOP AGAIN instantly.
                updated_state.matched_shelters =[]
                updated_state.trigger_new_db_search = False
                updated_state.selected_shelter_ids =[]
                
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
        
        # FIX: Check current_state, which is now guaranteed to be the final updated state
        if current_state.workflow_status == ShelterWorkflowStatus.COMPLETED:
            response.reply_message = "I have confirmed your selection and sent your details to the shelter manager. Please proceed to the location using the map link provided."
            
            # Control passed to orchestrator
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR

        else:
            if not current_state.next_question_for_user:
                response.reply_message = "I am processing your preferences to find the safest nearby options..."
                current_state.trigger_new_db_search = True 
            else:
                response.reply_message = current_state.next_question_for_user
            
        return response