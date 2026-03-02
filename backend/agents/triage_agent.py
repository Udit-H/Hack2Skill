import os
import jinja2
import instructor
from openai import AsyncOpenAI

from models.session import SessionState, AgentResponse, AgentActionType, AgentType
from models.triage import TriageState, TriageWorkflowStatus
from config.config import get_settings

class TriageAgent:
    def __init__(self):
        settings = get_settings()

        self.client = instructor.from_openai(AsyncOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url
        ), mode=instructor.Mode.JSON)
        
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))

    async def get_triage_system_prompt(self, current_state: TriageState, memory_context: str) -> str:
        template = self.template_env.get_template("triage_agent_system.j2")
        return template.render(
            current_state_json=current_state.model_dump_json(),
            memory_context=memory_context
        )

    async def process_turn(self, session: SessionState, memory_manager, user_message: str = None) -> AgentResponse:
        # Initialize Triage state if it doesn't exist yet
        if not session.triage:
            session.triage = TriageState()
            
        current_state = session.triage
        memory_context = memory_manager.get_memory_context()
        
        system_prompt = await self.get_triage_system_prompt(current_state, memory_context)

        # Let the LLM evaluate the facts and advance the workflow
        updated_state: TriageState = await self.client.chat.completions.create(
            model="gemini-2.5-flash", 
            response_model=TriageState,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message or "Hello."}
            ]
        )

        session.triage = updated_state

        # --- ORCHESTRATOR INSTRUCTIONS ---
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)
        
        if updated_state.workflow_status == TriageWorkflowStatus.COMPLETED:
            # We have all the profiling data. Tell the Orchestrator to take over!
            response.reply_message = "Thank you for sharing this. Let me coordinate our next steps based on what you need."
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
        else:
            response.reply_message = updated_state.next_question_for_user
            
        return response