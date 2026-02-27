import asyncio
import uuid
import sys

# Import your models and core logic
from models.session import SessionState, AgentType, AgentActionType
from models.triage import TriageState
from models.legal import LegalAgentState, WorkflowStatus
from models.enums import CrisisCategory
from core.memory import MemoryManager
from agents.legal_agent import LegalAgent

async def main():
    # 1. Generate a unique session for this test
    session_id = f"test-cli-{str(uuid.uuid4())[:6]}"
    print(f"==================================================")
    print(f"🚀 STARTING CLI ORCHESTRATOR TEST")
    print(f"Session ID: {session_id}")
    print(f"==================================================\n")
    
    # 2. Initialize Components
    try:
        memory = MemoryManager(session_id)
        legal_agent = LegalAgent()
    except Exception as e:
        print(f"❌ Initialization Error (Is Redis running on port 10908?): {e}")
        sys.exit(1)

    # 3. Mock the Global State (Simulating a finished Triage phase)
    session = SessionState(
        session_id=session_id,
        user_phone="+919999999999", # Required now
        active_agent=AgentType.LEGAL,
        triage=TriageState(
            category=CrisisCategory.ILLEGAL_EVICTION,
            urgency_level=5,
            needs_immediate_shelter=True,
            physical_danger_present=True,
            incident_summary="User is Ram. Landlord locked him out yesterday. No access to belongings.",
            has_ownership_claim=False, # Required now
            is_financially_destitute=False # Required now
        ),
        legal=LegalAgentState(
            workflow_status=WorkflowStatus.AWAITING_DOCS,
            drafts_to_generate=[]
        )
    )

    print("[SYSTEM]: Orchestrator has mocked the Triage State.")
    print("[SYSTEM]: Handing control to Legal Agent...")
    print("[SYSTEM]: Type 'exit' to quit. Type 'upload' to simulate uploading a rent agreement.\n")

    # 4. The Interactive Chat Loop
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['exit', 'quit']:
            print("\n[SYSTEM]: Exiting CLI Test.")
            break
            
        doc_path = None
        if user_input.lower() == 'upload':
            doc_path = "./mock_rent_agreement.pdf" # Make sure to point this to a real test file if testing OCR
            user_input = "I am uploading my rent agreement now."
            print("📎 [SYSTEM]: Simulating document upload...")

        print("🤖 [Agent is thinking...]")
        
        try:
            # A. Execute the Agent
            response = await legal_agent.process_turn(
                session=session, 
                memory_manager=memory,
                user_message=user_input, 
                document_path=doc_path
            )
            
            # B. Print the Agent's Reply
            print(f"\nSahayak: {response.reply_message}\n")
            
            # C. Update Memory (Fires background summarization if threshold met)
            memory.add_turn(user_message=user_input, ai_message=response.reply_message)
            
            # D. Orchestrator Handoff Check
            if response.action_type == AgentActionType.SWITCH_AGENT:
                print(f"==================================================")
                print(f"🛑 AGENT SWITCH TRIGGERED")
                print(f"Legal Agent is finished. Next requested agent: {response.next_active_agent.value}")
                print(f"Final Legal State JSON:")
                print(session.legal.model_dump_json(indent=2))
                print(f"==================================================")
                break

        except Exception as e:
            print(f"\n❌ Execution Error: {e}")
            break

if __name__ == "__main__":
    # Windows fix for asyncio if needed:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())