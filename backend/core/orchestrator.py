import logging
from models.session import SessionState, AgentType, AgentActionType
from models.triage import TriageWorkflowStatus
from models.shelter import ShelterWorkflowStatus
from models.legal import WorkflowStatus as LegalWorkflowStatus
from models.drafting import DraftingWorkflowStatus

from agents.triage_agent import TriageAgent
from agents.shelter_agent import ShelterAgent
from agents.legal_agent import LegalAgent
from agents.drafting_agent import DraftingAgent

class Orchestrator:
    def __init__(self):
        # Initialize the stateless sub-agents
        self.triage_agent = TriageAgent()
        self.shelter_agent = ShelterAgent()
        self.legal_agent = LegalAgent()
        self.drafting_agent = DraftingAgent()

    async def handle_turn(
        self, 
        session: SessionState, 
        memory_manager, 
        user_message: str, 
        document_path: str = None
    ) -> str:
        """
        The main entry point for every single user message.
        Evaluates state, routes to the correct agent, and handles handoffs.
        """
        
        # 2. EVALUATE ROUTING RULES (If Orchestrator currently holds control)
        if session.active_agent in[AgentType.ORCHESTRATOR, AgentType.COMPLETED]:
            self._determine_next_agent(session)

        # 3. DISPATCH TO ACTIVE AGENT
        response = await self._dispatch_to_agent(session, memory_manager, user_message, document_path)

        final_reply = response.reply_message

        # 4. HANDLE SEAMLESS HANDOFFS
        # If the agent just finished its job, it will return SWITCH_AGENT.
        if response.action_type == AgentActionType.SWITCH_AGENT:
            logging.info(f"Agent Handoff Triggered. Old Agent finished.")
            
            # Recalculate routing rules to find the NEXT agent
            self._determine_next_agent(session)
            logging.info(f"Orchestrator routed next step to: {session.active_agent.value}")
            
            # If there is another task to do, instantly trigger the next agent's opening message!
            if session.active_agent != AgentType.COMPLETED:
                next_agent_response = await self._dispatch_to_agent(session, memory_manager, user_message=None, document_path=None)
                
                # Combine the goodbye message of Agent A with the opening message of Agent B
                final_reply = f"{response.reply_message}\n\n{next_agent_response.reply_message}"

        return final_reply


    # --------------------------------------------------------------------------------
    # ROUTING & DISPATCH LOGIC
    # --------------------------------------------------------------------------------

    def _determine_next_agent(self, session: SessionState):
        """
        The strict mathematical rules engine for your workflow:
        Order: Triage -> Shelter (If Needed) -> Legal (If Needed) -> Completed
        """
        triage = session.triage
        shelter = session.shelter
        legal = session.legal

        # RULE 1: Triage is always first.
        if triage is None or triage.workflow_status != TriageWorkflowStatus.COMPLETED:
            session.active_agent = AgentType.TRIAGE
            return

        # RULE 2: Shelter is second (Only if Triage explicitly flagged it as needed).
        if triage.needs_immediate_shelter:
            if shelter is None or shelter.workflow_status != ShelterWorkflowStatus.COMPLETED:
                session.active_agent = AgentType.SHELTER
                return

        # RULE 3: Legal is third (Only if Triage explicitly flagged it AND Shelter is done/skipped).
        if triage.needs_legal_action:
            if legal is None or legal.workflow_status != LegalWorkflowStatus.READY_TO_DRAFT:
                session.active_agent = AgentType.LEGAL
                return

        # RULE 4: Drafting is fourth (if Legal finished with drafts OR Shelter finished with consent)
        drafting = session.drafting
        has_legal_drafts = (legal and legal.workflow_status == LegalWorkflowStatus.READY_TO_DRAFT 
                           and legal.drafts_to_generate)
        has_shelter_consent = (shelter and shelter.workflow_status == ShelterWorkflowStatus.COMPLETED 
                              and shelter.user_consent_to_share)
        
        if has_legal_drafts or has_shelter_consent:
            if drafting is None or drafting.workflow_status != DraftingWorkflowStatus.COMPLETED:
                session.active_agent = AgentType.DRAFTING
                return

        # RULE 5: Everything is done.
        session.active_agent = AgentType.COMPLETED


    async def _dispatch_to_agent(self, session: SessionState, memory_manager, user_message: str, document_path: str):
        """Routes the execution to the correct Python Class."""
        
        if session.active_agent == AgentType.TRIAGE:
            return await self.triage_agent.process_turn(session, memory_manager, user_message)
            
        elif session.active_agent == AgentType.SHELTER:
            return await self.shelter_agent.process_turn(session, memory_manager, user_message)
            
        elif session.active_agent == AgentType.LEGAL:
            return await self.legal_agent.process_turn(session, memory_manager, user_message, document_path)
        
        elif session.active_agent == AgentType.DRAFTING:
            return await self.drafting_agent.process_turn(session, memory_manager, user_message)
            
        elif session.active_agent == AgentType.COMPLETED:
            # Fallback if the user keeps typing after everything is done
            from models.session import AgentResponse # Lazy import to avoid circular issues
            return AgentResponse(
                action_type=AgentActionType.REPLY_TO_USER,
                reply_message="All our current tasks are completed. If your situation has escalated, please type 'Help' to restart the emergency protocols."
            )