"""
Sahayak CLI Test — Mirrors the exact backend flow used by the frontend.
Uses the same Orchestrator, MemoryManager, ChatStorageService as main.py's /api/chat.

In DynamoDB memory mode (default), memory.add_turn() is a no-op.
Conversation context comes from ChatStorageService → DynamoDB → MemoryManager reads.
So we MUST persist via chat_storage for agents to see prior turns.

Usage:
    cd backend
    python playground/test_cli.py

Commands:
    exit/quit   — Exit the CLI
    status      — Print full session state JSON
    upload      — Simulate a document upload
    location    — Set GPS coords (e.g. "location 12.97 77.64" or just "location")
"""

import asyncio
import uuid
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from models.session import SessionState, AgentType
from core.memory import MemoryManager
from core.orchestrator import Orchestrator
from services.chat_storage_service import ChatStorageService

# ── Terminal colors ──────────────────────────────────────
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
RED     = "\033[91m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
RESET   = "\033[0m"


async def main():
    session_id = f"test-cli-{str(uuid.uuid4())[:6]}"
    mem_backend = os.getenv("MEMORY_BACKEND", "dynamodb")

    print(f"\n{BOLD}{'=' * 60}")
    print(f"  🚀 SAHAYAK — End-to-End CLI Test")
    print(f"  Session:  {session_id}")
    print(f"  Memory:   {mem_backend}")
    print(f"{'=' * 60}{RESET}\n")

    # ── 1. Initialize — same as main.py get_or_create_session ────────
    try:
        memory       = MemoryManager(session_id)
        orchestrator = Orchestrator()
        chat_storage = ChatStorageService()

        session = SessionState(
            session_id=session_id,
            user_phone="+91-test-cli",
            active_agent=AgentType.ORCHESTRATOR,
        )
    except Exception as e:
        print(f"{RED}❌ Initialization Error: {e}{RESET}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(f"  {GREEN}✔ Orchestrator ready{RESET}")
    print(f"  {GREEN}✔ Memory ({mem_backend}) ready{RESET}")
    print(f"  {GREEN}✔ Chat storage (DynamoDB) ready{RESET}")
    print()
    print(f"  {DIM}Commands: exit | status | upload | location [lat lng]{RESET}")
    print(f"  {DIM}{'─' * 55}{RESET}\n")

    # ── 2. Auto-trigger "Hello" to start Triage Agent greeting ───────
    user_input = "Hello"
    print(f"  {YELLOW}You:{RESET} {user_input} {DIM}(auto-triggered){RESET}")
    doc_path = None

    # ── 3. Main Chat Loop ────────────────────────────────────────────
    while True:
        print(f"  {DIM}🤖 [Agent thinking...]{RESET}")

        try:
            # ── A. Route through Orchestrator (mirrors main.py /api/chat) ──
            ai_reply = await orchestrator.handle_turn(
                session=session,
                memory_manager=memory,
                user_message=user_input,
                document_path=doc_path,
            )

            # ── B. Print response ──
            print(f"\n  {CYAN}Sahayak:{RESET} {ai_reply}\n")

            # Show metadata from last_agent_response (same fields main.py returns)
            if session.last_agent_response:
                meta = session.last_agent_response
                if meta.get("error_message"):
                    print(f"  {RED}⚠ Error: {meta['error_message']}{RESET}")
                if meta.get("download_urls"):
                    print(f"  {GREEN}📥 Downloads:{RESET}")
                    for url in meta["download_urls"]:
                        print(f"       {url}")
                if meta.get("progress_status"):
                    print(f"  {DIM}Progress: {meta['progress_status']}{RESET}")
                print()

            # ── C. Update Memory (no-op in DynamoDB mode, but call anyway) ──
            memory.add_turn(user_message=user_input, ai_message=ai_reply)

            # ── D. Persist to DynamoDB ChatStorage (CRITICAL in DynamoDB mode) ──
            #    Without this, memory.get_memory_context() returns empty on next turn
            #    because it reads from the sahayak-chat-messages table.
            try:
                user_id = session.user_phone or "+91-test-cli"

                await chat_storage.save_message(
                    session_id=session_id,
                    role="user",
                    content=user_input,
                    agent_type=session.active_agent.value,
                    user_id=user_id,
                )

                response_metadata = {}
                if session.last_agent_response:
                    response_metadata = {
                        "progress_status": session.last_agent_response.get("progress_status"),
                        "is_loading": session.last_agent_response.get("is_loading"),
                        "error_message": session.last_agent_response.get("error_message"),
                        "download_urls": session.last_agent_response.get("download_urls"),
                    }

                await chat_storage.save_message(
                    session_id=session_id,
                    role="assistant",
                    content=ai_reply,
                    agent_type=session.active_agent.value,
                    metadata=response_metadata if response_metadata else None,
                    user_id=user_id,
                )
            except Exception as e:
                print(f"  {DIM}[⚠ Chat storage write skipped: {e}]{RESET}")

            # ── E. Check completion ──
            if session.active_agent == AgentType.COMPLETED:
                print(f"\n{BOLD}{'=' * 60}")
                print(f"  ✅ ALL WORKFLOWS COMPLETED")
                print(f"{'=' * 60}{RESET}\n")

                if session.drafting and session.drafting.generated_drafts:
                    print(f"  {GREEN}📄 Generated Documents:{RESET}")
                    for d in session.drafting.generated_drafts:
                        status = "✓" if d.download_url else "✗"
                        print(f"     {status} {d.title}")
                        if d.download_url:
                            print(f"       ↳ {d.download_url}")
                    print()

                if session.drafting and session.drafting.errors:
                    print(f"  {RED}⚠ Drafting Errors:{RESET}")
                    for err in session.drafting.errors:
                        print(f"     • {err}")
                    print()

                print(f"  {DIM}Session: {session_id}{RESET}")
                break

        except Exception as e:
            print(f"\n  {RED}❌ Execution Error: {e}{RESET}")
            import traceback; traceback.print_exc()
            break

        # ── F. Get next user input ──
        try:
            user_input = input(f"  {YELLOW}You:{RESET} ").strip()
        except EOFError:
            break

        doc_path = None

        if not user_input:
            print(f"  {DIM}[Please type a message, or 'exit' to quit]{RESET}")
            continue

        if user_input.lower() in ["exit", "quit"]:
            print(f"\n  {DIM}[Exiting CLI Test]{RESET}")
            break

        elif user_input.lower() == "status":
            print(f"\n  {BOLD}── Session State ({session.active_agent.value}) ──{RESET}")
            print(session.model_dump_json(indent=2))
            print(f"  {BOLD}{'─' * 50}{RESET}\n")
            user_input = "What were we discussing?"

        elif user_input.lower() == "upload":
            doc_path = "./mock_rent_agreement.pdf"
            user_input = "I am uploading my rent agreement now."
            print(f"  {DIM}📎 [Simulating document upload...]{RESET}")

        elif user_input.lower().startswith("location"):
            # "location 12.9716 77.6412" or just "location" for default Bengaluru
            parts = user_input.split()
            if len(parts) >= 3:
                lat, lng = float(parts[1]), float(parts[2])
            else:
                lat, lng = 12.9716, 77.5946  # Central Bengaluru

            # Mirror main.py GPS injection logic exactly
            if not session.shelter:
                from models.shelter import ShelterAgentState
                session.shelter = ShelterAgentState()
            session.shelter.user_coordinates = {"lat": lat, "lng": lng}
            if not session.shelter.user_location_text:
                session.shelter.user_location_text = f"{lat},{lng}"
            if not session.shelter.user_preferences:
                session.shelter.user_preferences = "No specific requirements"

            print(f"  {GREEN}📍 GPS set to ({lat}, {lng}){RESET}")
            user_input = "I am sending my live location pin."


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n  {DIM}[Interrupted. Exiting...]{RESET}")
    finally:
        try:
            loop = asyncio.get_event_loop()
            for task in asyncio.all_tasks(loop):
                task.cancel()
        except RuntimeError:
            pass