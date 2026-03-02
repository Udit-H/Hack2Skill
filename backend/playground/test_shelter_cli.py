import asyncio
import uuid
import sys

from models.session import SessionState, AgentType, AgentActionType
from models.triage import TriageState
from models.shelter import ShelterAgentState, ShelterWorkflowStatus
from models.enums import CrisisCategory
from core.memory import MemoryManager
from agents.shelter_agent import ShelterAgent 

async def main():
    # 1. Generate a unique session for this test
    session_id = f"test-shelter-{str(uuid.uuid4())[:6]}"
    print(f"==================================================")
    print(f"🚀 STARTING SHELTER AGENT CLI TEST")
    print(f"Session ID: {session_id}")
    print(f"==================================================\n")
    
    # 2. Initialize Components
    try:
        memory = MemoryManager(session_id)
        shelter_agent = ShelterAgent()
    except Exception as e:
        print(f"❌ Initialization Error (Redis/Supabase/LLM setup missing?): {e}")
        sys.exit(1)

    # 3. Mock the Global State (Simulating a finished Triage phase)
    session = SessionState(
        session_id=session_id,
        user_phone="+919999999999",
        active_agent=AgentType.SHELTER,
        triage=TriageState(
            # Using Domestic Violence to test strict category filtering in DB
            category=CrisisCategory.DOMESTIC_VIOLENCE, 
            urgency_level=5,
            needs_immediate_shelter=True,
            physical_danger_present=True,
            incident_summary="User is Rahul. He is fleeing an abusive situation at home and is currently on the street. Needs a safe place immediately.",
            has_ownership_claim=False,
            is_financially_destitute=True
        ),
        shelter=ShelterAgentState(
            workflow_status=ShelterWorkflowStatus.AWAITING_LOCATION,
            selected_shelter_ids=[],
            matched_shelters=[]
        )
    )

    print("[SYSTEM]: Orchestrator has mocked a Domestic Violence Triage State.")
    print("[SYSTEM]: Handing control to Shelter Agent...")
    print("[SYSTEM]: Type 'exit' to quit.")
    print("[SYSTEM]: Type 'gps' to simulate sending a WhatsApp Live Location pin.\n")

    # 4. The Interactive Chat Loop
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("\n[SYSTEM]: Exiting CLI Test.")
            break
            
        # Mocking a WhatsApp GPS Pin drop
        if user_input.lower() == 'gps':
            # Setting coordinates (e.g., Connaught Place, New Delhi)
            session.shelter.user_coordinates = {'lat': 12.9803, 'lng': 77.5688}
            user_input = "I am sending my live location pin."
            print("📍 [SYSTEM]: Simulating WhatsApp GPS Pin Drop...")

        print("🤖 [Agent is thinking and querying Supabase...]")
        
        try:
            # A. Execute the Agent
            response = await shelter_agent.process_turn(
                session=session, 
                memory_manager=memory,
                user_message=user_input
            )
            
            # B. Print the Agent's Reply
            print(f"\nSahayak: {response.reply_message}\n")
            
            # C. Update Memory
            memory.add_turn(user_message=user_input, ai_message=response.reply_message)
            
            # D. Orchestrator Handoff Check
            if response.action_type == AgentActionType.SWITCH_AGENT:
                print(f"==================================================")
                print(f"🛑 AGENT SWITCH TRIGGERED (SHELTER COMPLETED)")
                print(f"Final Shelter State JSON:")
                print(session.shelter.model_dump_json(indent=2))
                print(f"==================================================")
                break

        except Exception as e:
            print(f"\n❌ Execution Error: {e}")
            break

if __name__ == "__main__":
    # Windows fix for asyncio if needed
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())