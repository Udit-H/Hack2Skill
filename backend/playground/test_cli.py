import asyncio
import uuid
import sys

from models.session import SessionState, AgentType
from core.memory import MemoryManager
from core.orchestrator import Orchestrator

async def main():
    session_id = f"test-cli-{str(uuid.uuid4())[:6]}"
    print(f"==================================================")
    print(f"🚀 STARTING END-TO-END AI SYSTEM CLI TEST")
    print(f"Session ID: {session_id}")
    print(f"==================================================\n")
    
    # 1. Initialize System Components
    try:
        memory = MemoryManager(session_id)
        orchestrator = Orchestrator()
        
        # Initialize a completely blank global state.
        # Active agent starts as ORCHESTRATOR so it evaluates rules immediately.
        session = SessionState(
            session_id=session_id,
            active_agent=AgentType.ORCHESTRATOR
        )
    except Exception as e:
        print(f"❌ Initialization Error (Check Redis/Supabase connections): {e}")
        sys.exit(1)

    print("[SYSTEM]: Orchestrator and Memory initialized.")
    print("[SYSTEM]: Type 'exit' to quit. Type 'upload' to simulate a document upload.")
    print("[SYSTEM]: Type 'status' to print the current internal JSON state.\n")

    # 2. Kickstart the conversation
    # We pass an initial "Hello" to trigger the Triage Agent's greeting.
    user_input = "Hello"
    print(f"You: {user_input} (Auto-triggered to start system)")
    doc_path = None

    # 3. The Master Chat Loop
    while True:
        print("🤖[Agent is thinking...]")
        
        try:
            # A. Orchestrator handles routing, handoffs, and agent execution
            ai_response_text = await orchestrator.handle_turn(
                session=session,
                memory_manager=memory,
                user_message=user_input,
                document_path=doc_path
            )
            
            # B. Print the AI's Reply
            print(f"\nSahayak: {ai_response_text}\n")
            
            # C. Update Memory (Triggers async L2 summarization automatically)
            memory.add_turn(user_message=user_input, ai_message=ai_response_text)
            
            # D. Check if the entire lifecycle is completed
            if session.active_agent == AgentType.COMPLETED:
                print(f"==================================================")
                print(f"✅ ALL WORKFLOWS COMPLETED")
                print(f"Final Session State JSON:")
                print(session.model_dump_json(indent=2))
                print(f"==================================================")
                break

        except Exception as e:
            print(f"\n❌ Execution Error: {e}")
            break
            
        # E. Get Next User Input
        user_input = input("You: ")
        doc_path = None # Reset doc path
        
        if user_input.lower() in['exit', 'quit']:
            print("\n[SYSTEM]: Exiting CLI Test.")
            break
            
        elif user_input.lower() == 'status':
            print(f"\n--- CURRENT SYSTEM STATE ({session.active_agent.value}) ---")
            print(session.model_dump_json(indent=2))
            print("--------------------------------------------------\n")
            user_input = "What were we discussing?" # Keep the LLM moving
            
        elif user_input.lower() == 'upload':
            doc_path = "./mock_rent_agreement.pdf" # Point this to a real file if testing OCR later
            user_input = "I am uploading my rent agreement now."
            print("📎 [SYSTEM]: Simulating document upload...")

if __name__ == "__main__":    
    asyncio.run(main())