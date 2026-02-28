#!/usr/bin/env python3
"""
Simple Shelter Agent CLI - NO LLM NEEDED
Pure rule-based logic for testing
"""

import asyncio
from models.session import SessionState, AgentType
from models.shelter import ShelterAgentState, ShelterWorkflowStatus, UserShelterProfile, GeoLocation, ShelterProfile
from models.triage import TriageState
from models.enums import CrisisCategory


class SimpleShelterAgent:
    def __init__(self):
        self.mock_shelters = [
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
                distance_km=4.1,
                google_maps_url="https://maps.google.com/?q=28.5894,77.2254",
                capacity_available=True
            )
        ]
    
    async def process(self, state, message):
        """Process user message and update state"""
        msg_lower = message.lower()
        
        # State: AWAITING_LOCATION
        if state.workflow_status == ShelterWorkflowStatus.AWAITING_LOCATION:
            if any(word in msg_lower for word in ["delhi", "central", "kashmere", "karol", "lodi", "yamuna"]):
                state.workflow_status = ShelterWorkflowStatus.AWAITING_USER_DETAILS
                state.user_location = GeoLocation(latitude=28.6505, longitude=77.2303)
                return "Great! Now, to find the right shelter for you, could you tell me:\n- Are you a woman, man, or other?\n- Do you have children with you?"
            else:
                return "I understand you need shelter urgently. Where in Delhi are you located? (e.g., Central Delhi, Kashmere Gate, etc.)"
        
        # State: AWAITING_USER_DETAILS
        elif state.workflow_status == ShelterWorkflowStatus.AWAITING_USER_DETAILS:
            # Extract gender
            if "woman" in msg_lower or "female" in msg_lower:
                gender = "female"
            elif "man" in msg_lower or "male" in msg_lower:
                gender = "male"
            else:
                gender = "female"  # default
            
            # Extract children status
            has_children = any(word in msg_lower for word in ["child", "children", "kid", "daughter", "son"])
            
            state.user_profile = UserShelterProfile(gender=gender, has_children=has_children)
            
            # Filter shelters
            filtered = []
            for shelter in self.mock_shelters:
                if gender == "female":
                    if shelter.shelter_type in ["women_only", "women_children"]:
                        filtered.append(shelter)
                else:
                    if shelter.shelter_type == "mixed":
                        filtered.append(shelter)
            
            state.matched_shelters = filtered[:3]
            state.workflow_status = ShelterWorkflowStatus.SEARCHING_SHELTERS
            
            if filtered:
                shelter_list = "\n".join([f"  {i+1}. {s.name} - {s.distance_km}km away" for i, s in enumerate(filtered)])
                return f"Perfect! I found {len(filtered)} shelters near you:\n\n{shelter_list}\n\nWhich one would you like me to contact? (Say '1', '2', or 'first', 'second')"
            else:
                return "I'm sorry, no shelters are currently available for your profile. Let me help you find alternatives."
        
        # State: SEARCHING_SHELTERS
        elif state.workflow_status == ShelterWorkflowStatus.SEARCHING_SHELTERS:
            if any(word in msg_lower for word in ["1", "first", "one"]):
                shelter_idx = 0
            elif any(word in msg_lower for word in ["2", "second", "two"]):
                shelter_idx = 1
            elif any(word in msg_lower for word in ["3", "third", "three"]):
                shelter_idx = 2
            else:
                shelter_idx = 0  # default first
            
            if state.matched_shelters and len(state.matched_shelters) > shelter_idx:
                state.selected_shelter = state.matched_shelters[shelter_idx]
                state.workflow_status = ShelterWorkflowStatus.SHELTER_MATCHED
                
                s = state.selected_shelter
                print(f"\n[SMS] Sending notification to {s.name} at {s.contact_number}")
                
                return f"✅ CONFIRMED!\n\nI've notified {s.name} about your arrival.\n\n📍 Address: {s.address}\n📞 Contact: {s.contact_number}\n📏 Distance: {s.distance_km}km\n🗺️ Directions: {s.google_maps_url}\n\nPlease head there now. They're expecting you! Stay safe. 💙"
            else:
                return "Which shelter would you prefer? Say the number (1, 2, or 3)."
        
        # State: SHELTER_MATCHED
        elif state.workflow_status == ShelterWorkflowStatus.SHELTER_MATCHED:
            return "Your shelter is confirmed! Is there anything else you need help with?"
        
        return "I'm here to help. What do you need?"


async def main():
    print("\n" + "="*70)
    print("🏠 SHELTER AGENT - SIMPLE CLI (NO LLM)")
    print("="*70 + "\n")
    
    agent = SimpleShelterAgent()
    state = ShelterAgentState()
    
    print("💬 Start chatting! Type 'exit' to quit\n")
    print("🤖 Agent: I understand you need emergency shelter. Where are you located?\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "exit":
                print("\n👋 Goodbye! Stay safe!")
                break
            
            response = await agent.process(state, user_input)
            print(f"\n🤖 Agent: {response}\n")
            print(f"   [Status: {state.workflow_status}]\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
