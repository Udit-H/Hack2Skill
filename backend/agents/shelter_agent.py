import os
import jinja2
import google.generativeai as genai

from config.config import get_settings
from models.shelter import (
    ShelterAgentState, 
    ShelterWorkflowStatus, 
    GeoLocation, 
    ShelterProfile,
    UserShelterProfile
)
from models.triage import TriageState
from models.session import SessionState, AgentResponse, AgentActionType, AgentType


class ShelterAgent:
    def __init__(self):
        settings = get_settings()
        
        genai.configure(api_key=settings.llm.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))
    
    async def get_shelter_system_prompt(
        self, 
        triage: TriageState, 
        current_state: ShelterAgentState
    ) -> str:
        """
        Renders the modular Jinja2 system prompt by injecting context.
        """
        
        template = self.template_env.get_template("shelter_agent_system.j2")
        state_json = current_state.model_dump_json()
        
        return template.render(
            triage_category=triage.category.value if triage.category else "Unknown",
            incident_summary=triage.incident_summary,
            current_state_json=state_json,
            user_location=current_state.user_location,
            matched_shelters=current_state.matched_shelters
        )
    
    async def search_nearby_shelters(
        self, 
        location: GeoLocation, 
        user_profile: UserShelterProfile
    ) -> list[ShelterProfile]:
        """
        Search for nearby shelters based on location and user profile.
        In production, this would query a real database/API.
        """
        # Mock shelter data for Delhi
        mock_shelters = [
            ShelterProfile(
                shelter_id=1,
                name="Delhi Women's Shelter - Kasturba Niketan",
                shelter_type="women_only",
                address="New Rohtak Road, Karol Bagh, New Delhi - 110005",
                contact_number="+91-11-2362-7348",
                distance_km=2.5,
                google_maps_url="https://maps.google.com/?q=28.6472,77.1946",
                capacity_available=True
            ),
            ShelterProfile(
                shelter_id=2,
                name="Night Shelter - Yamuna Bazaar",
                shelter_type="mixed",
                address="Yamuna Bazaar, Civil Lines, New Delhi - 110054",
                contact_number="+91-11-2393-8989",
                distance_km=3.2,
                google_maps_url="https://maps.google.com/?q=28.6672,77.2363",
                capacity_available=True
            ),
            ShelterProfile(
                shelter_id=3,
                name="Nirmal Chhaya Complex - Women & Children",
                shelter_type="women_children",
                address="Lodhi Road, New Delhi - 110003",
                contact_number="+91-11-2436-2612",
                distance_km=1.1,
                google_maps_url="https://maps.google.com/?q=28.5894,77.2254",
                capacity_available=False
            )
        ]
        
        # Filter based on user profile
        filtered_shelters = []
        for shelter in mock_shelters:
            if user_profile.gender == "female" and shelter.shelter_type in ["women_only", "women_children"]:
                filtered_shelters.append(shelter)
            elif shelter.shelter_type == "mixed":
                filtered_shelters.append(shelter)
        
        # Return only available shelters, sorted by distance
        available_shelters = [s for s in filtered_shelters if s.capacity_available]
        return sorted(available_shelters, key=lambda x: x.distance_km)[:3]
    
    async def dispatch_sms_to_shelter(self, shelter: ShelterProfile, user_profile: UserShelterProfile):
        """
        Mock SMS dispatch to shelter manager.
        In production, this would use Twilio/SMS Gateway.
        """
        # Mock implementation
        print(f"[SMS] Dispatched to {shelter.name} at {shelter.contact_number}")
        print(f"[SMS] User profile: {user_profile.model_dump_json()}")
        return True
    
    async def process_turn(
        self, 
        session: SessionState,
        user_message: str = None,
        memory_manager = None,
    ) -> AgentResponse:
        """
        The main asynchronous entry point. Orchestrates the shelter workflow.
        """
        
        triage = session.triage
        current_state = session.shelter
        
        if not current_state:
            current_state = ShelterAgentState()
            session.shelter = current_state
        
        memory_context = memory_manager.get_memory_context() if memory_manager else ""
        
        system_prompt = await self.get_shelter_system_prompt(triage, current_state)
        
        # Call Gemini API - use async version
        prompt = f"""{system_prompt}

Memory Context: {memory_context}

User Message: {user_message or "Evaluate the state and dictate the next workflow step."}

Respond with a helpful, empathetic message to the user. Keep it concise and supportive."""
        
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text
        except Exception as e:
            print(f"[WARNING] Gemini API error: {e}")
            response_text = "I'm here to help you find shelter."
        
        # Update state based on user message
        if current_state.workflow_status == ShelterWorkflowStatus.AWAITING_LOCATION:
            if any(word in user_message.lower() for word in ["delhi", "kashmere", "central", "lodi", "yamuna", "karol", "new", "south", "north", "east", "west"]):
                current_state.workflow_status = ShelterWorkflowStatus.AWAITING_USER_DETAILS
        
        elif current_state.workflow_status == ShelterWorkflowStatus.AWAITING_USER_DETAILS:
            if any(word in user_message.lower() for word in ["woman", "female", "male", "man", "child", "children", "kid"]):
                # Extract gender
                if "woman" in user_message.lower() or "female" in user_message.lower():
                    current_state.user_profile = UserShelterProfile(gender="female", has_children="child" in user_message.lower() or "children" in user_message.lower())
                else:
                    current_state.user_profile = UserShelterProfile(gender="male", has_children="child" in user_message.lower())
                
                current_state.workflow_status = ShelterWorkflowStatus.SEARCHING_SHELTERS
                
                # Search shelters
                current_state.matched_shelters = await self.search_nearby_shelters(
                    GeoLocation(latitude=28.6505, longitude=77.2303),  # Delhi default
                    current_state.user_profile
                )
        
        elif current_state.workflow_status == ShelterWorkflowStatus.SEARCHING_SHELTERS:
            if any(word in user_message.lower() for word in ["yes", "contact", "first", "please", "ok"]):
                if current_state.matched_shelters:
                    current_state.selected_shelter = current_state.matched_shelters[0]
                    current_state.workflow_status = ShelterWorkflowStatus.SHELTER_MATCHED
                    await self.dispatch_sms_to_shelter(current_state.selected_shelter, current_state.user_profile)
        
        session.shelter = current_state
        

        # Build the exact instruction for the Orchestrator
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
        
        if current_state.workflow_status == ShelterWorkflowStatus.AWAITING_LOCATION:
            response.reply_message = "I understand you need immediate shelter. To find the nearest safe shelter, could you share your current location? You can share your GPS coordinates, or simply tell me your current area/landmark in Delhi."
        
        elif current_state.workflow_status == ShelterWorkflowStatus.AWAITING_USER_DETAILS:
            response.reply_message = "To help me find the most appropriate shelter for you, could you share: Are you seeking shelter alone or with children? And your preferred gender if relevant?"
            
        elif current_state.workflow_status == ShelterWorkflowStatus.SEARCHING_SHELTERS:
            if current_state.matched_shelters:
                shelter_list = "\n".join([
                    f"  {i+1}. {s.name} - {s.distance_km}km away"
                    for i, s in enumerate(current_state.matched_shelters[:3])
                ])
                response.reply_message = f"Great! I found {len(current_state.matched_shelters)} shelters near you:\n\n{shelter_list}\n\nWhich one would you like me to contact?"
            else:
                response.reply_message = "I apologize, but the nearest shelters are currently at full capacity. Let me help you find alternative options."
                    
        elif current_state.workflow_status == ShelterWorkflowStatus.AWAITING_CONFIRMATION:
            response.reply_message = "Please let me know which shelter you'd like me to contact."
            
        elif current_state.workflow_status == ShelterWorkflowStatus.SHELTER_MATCHED:
            if current_state.selected_shelter:
                response.reply_message = f"✅ Confirmed! I've notified **{current_state.selected_shelter.name}** about your arrival.\n📍 {current_state.selected_shelter.address}\n📞 {current_state.selected_shelter.contact_number}\n\nPlease head there now. Stay safe!"
            else:
                response.reply_message = "Your shelter is confirmed. Is there anything else you need?"
                
        elif current_state.workflow_status == ShelterWorkflowStatus.FOLLOW_UP:
            response.reply_message = "Is there anything else I can help you with?"
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
        
        return response
