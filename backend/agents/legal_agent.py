import os
import jinja2
import instructor
from openai import AsyncOpenAI 

from config.config import get_settings
from models.legal import LegalAgentState, DraftType, LegalDraftPayload, WorkflowStatus
from models.triage import TriageState
from models.session import SessionState, AgentResponse, AgentActionType, AgentType # FIX: Added Global States
from core.rag_service import RagFlowService
from core.ocr_service import DocumentIntelligenceService 

# Remove this line later
from core.memory import MemoryManager


class LegalAgent:
    def __init__(self):
        settings = get_settings()
        
        self.client = instructor.from_openai(AsyncOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url
        ), mode=instructor.Mode.JSON)
        
        self.ocr_service = DocumentIntelligenceService()
        # self.rag_service = RagFlowService()
        
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))
    
    async def get_legal_system_prompt(
        self, 
        triage: TriageState, 
        current_state: LegalAgentState,
        document_path: str = None
    ) -> str:
        """
        Renders the modular Jinja2 system prompt by injecting context.
        """

        # --- PHASE 1: DATA GATHERING (OCR & RAG) ---
        if document_path and not current_state.extracted_doc_data:
            try:
                ocr_result = await self.ocr_service.analyze(source=document_path)
                current_state.extracted_doc_data = ocr_result.get("content", "OCR returned no text.")
            except Exception as e:
                current_state.extracted_doc_data = f"OCR failed: {str(e)}"

        # Async RAG
        if not current_state.retrieved_legal_context:
            rag_query = f"Delhi laws regarding {triage.category.value}: {triage.incident_summary}"
            # current_state.retrieved_legal_context = await self.rag_service.fetch_legal_context(rag_query)
            # Mocking RAG for now
            current_state.retrieved_legal_context = "Delhi Rent Control Act applies. Police Intimation under BNS 126 for wrongful restraint."

        template = self.template_env.get_template("legal_agent_system.j2")
        state_json = current_state.model_dump_json(exclude={"extracted_doc_data", "retrieved_legal_context"})
        
        return template.render(
            triage_category=triage.category.value if triage.category else "Unknown",
            incident_summary=triage.incident_summary,
            extracted_doc_data=current_state.extracted_doc_data,
            rag_context=current_state.retrieved_legal_context, # FIX: Passed RAG context to Jinja
            current_state_json=state_json
        )
    
    async def process_turn(
        self, 
        session: SessionState,  # FIX: Take the master SessionState 
        user_message: str = None, 
        document_path: str = None,
        memory_manager = None,
    ) -> AgentResponse: # FIX: Return Orchestrator instruction
        """
        The main asynchronous entry point. Orchestrates the workflow.
        """

        triage = session.triage
        current_state = session.legal
#         memory_context = memory_manager.get_memory_context()

#         system_prompt = await self.get_legal_system_prompt(triage, current_state, document_path)
#         updated_state: LegalAgentState = await self.client.chat.completions.create(
#             model="gemini-2.5-flash", 
#             response_model=LegalAgentState,
#             messages=[
#                 {"role": "system", "content": system_prompt},
# # ---------------------------------
# # remove the below line later
# # ---------------------------------
#                 {"role": "user", "content":memory_context + "\n use this memory context to gain idea about the current interaction"},
#                 {"role": "user", "content": user_message or "Evaluate the state and dictate the next workflow step."}
#             ]
#         )

        memory_context = memory_manager.get_memory_context()

        system_prompt = await self.get_legal_system_prompt(triage, current_state, document_path)

        updated_state: LegalAgentState = await self.client.chat.completions.create(
            model="gemini-2.5-flash", 
            response_model=LegalAgentState,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content":memory_context + "\n use this memory context to gain idea about the current interaction"},
                {"role": "user", "content": user_message or "Evaluate the state and dictate the next workflow step."}
            ]
        )

        session.legal = updated_state

        # Build the exact instruction for the Orchestrator
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)

        if updated_state.workflow_status == WorkflowStatus.AWAITING_DOCS:
            response.reply_message = "Please upload a clear photo of your rent agreement, eviction notice, or ID card so I can extract your details automatically."
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_USER_INFO:
            response.reply_message = updated_state.next_question_for_user
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_CONSENT:
            response.reply_message = "Filing a Police Intimation can escalate matters. Do I have your explicit permission to draft an intimation to the Delhi SHO regarding Wrongful Restraint?"
            
        elif updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT:
            response.reply_message = "I have successfully mapped your data to the official Delhi legal forms. The system will now generate your documents."
            
            # FIX: Crucial Orchestrator Handoff!
            # Legal work is done. Hand control back to Orchestrator to decide next steps (e.g. Shelter Agent)
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR

        return response

    def generate_pdf_from_jinja(self, draft: LegalDraftPayload) -> str:
        """
        Mock function. In reality, you will load an HTML Jinja template, 
        inject the 'draft' fields into it, and compile via pdfkit/weasyprint.
        """        
        # Example Implementation:
        # template = self.template_env.get_template(f"{draft.draft_type.value}.html.j2")
        # html_out = template.render(draft.dict())
        # pdf_path = f"/downloads/{draft.applicant_name}_{draft.draft_type.value}.pdf"
        # pdfkit.from_string(html_out, pdf_path)
        
        return f"/downloads/{draft.applicant_name}_{draft.draft_type.value}.pdf"