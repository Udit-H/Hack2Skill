import asyncio
from fastapi import BackgroundTasks
from models.session import SessionState, AgentType, AgentActionType
from models.legal import LegalAgentState
from agents.legal_agent import LegalAgent
# from core.triage_agent import TriageAgent
# from core.shelter_agent import ShelterAgent

class Orchestrator:
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.legal_agent = LegalAgent()
        self.shelter_agent = ShelterAgent()

    # --- FOREGROUND: Fast Webhook ---
    async def handle_incoming_webhook(self, user_id: str, message: str, doc_url: str, bg_tasks: BackgroundTasks):
        """Called directly by FastAPI endpoint. Returns 200 OK instantly."""
        
        # 1. Dispatch heavy lifting to Celery/BackgroundTasks
        bg_tasks.add_task(self.background_worker, user_id, message, doc_url)
        return {"status": "processing_in_background"}


    # --- BACKGROUND: The Routing Engine ---
    async def background_worker(self, user_id: str, message: str, doc_url: str):
        # 1. Load Global State from Redis
        session: SessionState = await load_session_from_redis(user_id)
        
        # 2. EMERGENCY OVERRIDE CHECK (The Wow Factor)
        if session.active_agent == AgentType.LEGAL and self._is_emergency_override(message):
            session.active_agent = AgentType.SHELTER
            await send_whatsapp(user_id, "I am pausing the legal work. Activating emergency shelter protocols.")

        # 3. ROUTE TO ACTIVE AGENT
        agent_response = None
        
        if session.active_agent == AgentType.ORCHESTRATOR:
            agent_response = await self.triage_agent.process_turn(session, message)
            
        elif session.active_agent == AgentType.LEGAL:
            agent_response = await self.legal_agent.process_turn(session, message, doc_url)
            
        elif session.active_agent == AgentType.SHELTER:
            agent_response = await self.shelter_agent.process_turn(session, message)

        # 4. HANDLE AGENT'S OUTPUT INSTRUCTIONS
        await self._execute_agent_response(session, agent_response, user_id)

        # 5. Save Global State back to Redis
        await save_session_to_redis(session)


    async def _execute_agent_response(self, session: SessionState, response, user_id: str):
        """Executes whatever the Agent told the Orchestrator to do."""
        
        if response.action_type == AgentActionType.REPLY_TO_USER:
            await send_whatsapp(user_id, response.reply_message)
            
        elif response.action_type == AgentActionType.SWITCH_AGENT:
            # e.g., Legal Agent finished. Orchestrator takes over to see what's next.
            session.active_agent = response.next_active_agent
            
            # If Orchestrator takes back control, immediately evaluate next steps
            if session.active_agent == AgentType.ORCHESTRATOR:
                await self._evaluate_next_orchestrator_step(session, user_id)

    async def _evaluate_next_orchestrator_step(self, session: SessionState, user_id: str):
        """The Master Logic: Decides what the user needs after Triage or after an agent finishes."""
        
        # Scenario 1: Triage just finished. We need Legal.
        if session.triage and session.triage.needs_legal_action and not session.legal:
            session.active_agent = AgentType.LEGAL
            # Initialize empty legal state
            session.legal = LegalAgentState(workflow_status="awaiting_docs", drafts_to_generate=[])
            await send_whatsapp(user_id, "Let's prepare your legal defense. Please upload your rent agreement or eviction notice.")

        # Scenario 2: Legal finished. Do they need a shelter?
        elif session.triage and session.triage.needs_immediate_shelter and not session.shelter:
            session.active_agent = AgentType.SHELTER
            session.shelter = ShelterAgentState(workflow_status="awaiting_consent")
            await send_whatsapp(user_id, "Your legal documents are ready. However, you indicated you are locked out. Do I have your consent to locate a nearby emergency shelter and send an application to the manager?")
            
        # Scenario 3: Everything is done.
        else:
            session.active_agent = AgentType.COMPLETED
            await send_whatsapp(user_id, "All operations completed. Stay safe, and type 'Hi' if you need more help.")

    def _is_emergency_override(self, message: str) -> bool:
        """Fast regex/keyword check to interrupt agents."""
        emergency_keywords =["help", "banging", "door", "hitting", "police", "scared", "street", "homeless"]
        return any(word in message.lower() for word in emergency_keywords)