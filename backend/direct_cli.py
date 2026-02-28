#!/usr/bin/env python3
"""
Direct CLI for Shelter Agent (No FastAPI server needed)
Just run: python direct_cli.py
"""

import asyncio
from models.session import SessionState, AgentType
from models.shelter import ShelterAgentState
from models.triage import TriageState
from models.enums import CrisisCategory
from core.memory import MemoryManager
from agents.shelter_agent import ShelterAgent


async def main():
    print("\n" + "="*70)
    print("🏠 SHELTER AGENT - DIRECT CLI (NO SERVER)")
    print("="*70 + "\n")
    
    # Initialize
    user_id = "cli-user"
    session = SessionState(
        session_id=user_id,
        user_phone="+919999999999",
        active_agent=AgentType.SHELTER,
        triage=TriageState(
            category=CrisisCategory.ILLEGAL_EVICTION,
            urgency_level=5,
            incident_summary="User needs emergency shelter",
            has_ownership_claim=False,
            is_financially_destitute=True,
            needs_immediate_shelter=True,
            physical_danger_present=False
        ),
        shelter=ShelterAgentState()
    )
    
    memory = MemoryManager(user_id)
    agent = ShelterAgent()
    
    print("💬 Start chatting! Type 'exit' to quit\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "exit":
                print("\n👋 Goodbye!")
                break
            
            # Call agent directly
            print("⏳ Processing...")
            response = await agent.process_turn(session, user_input, memory)
            
            print(f"\n🤖 Agent: {response.reply_message}")
            print(f"   Status: {session.shelter.workflow_status}\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
