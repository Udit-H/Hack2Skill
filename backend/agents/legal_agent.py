import os
import jinja2
import instructor
import boto3

from config.config import get_settings
from core.bedrock_client import BedrockInstructorClient, BedrockAsyncClient
from config.translations import get_translated_response
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
        
        # Initialize Bedrock client
        self.bedrock_client = BedrockInstructorClient(
            model_id=settings.llm.model_id,
            region_name=settings.llm.aws_region,
            aws_access_key_id=settings.llm.aws_access_key_id,
            aws_secret_access_key=settings.llm.aws_secret_access_key,
        )
        
        self.model_id = settings.llm.model_id
        
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
        if document_path and (not current_state.extracted_doc_data or current_state.extracted_doc_data.startswith("OCR failed")):
            try:
                ocr_result = await self.ocr_service.analyze(source=document_path)
                current_state.extracted_doc_data = ocr_result.get("content", "OCR returned no text.")
                print(f"✅ OCR succeeded: {len(current_state.extracted_doc_data)} chars extracted")
            except Exception as e:
                current_state.extracted_doc_data = f"OCR failed: {str(e)}"
                print(f"❌ OCR failed: {e}")

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
        language: str = "en",
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

        print(f"\n📋 Legal Agent Input:")
        print(f"   Current Status: {current_state.workflow_status}")
        print(f"   Document Data: {'✅ Present' if current_state.extracted_doc_data else '❌ Missing'}")
        print(f"   Has Consent: {current_state.user_consent_police if current_state.user_consent_police is not None else 'Not set'}")
        print(f"   User Message: {user_message[:100] if user_message else 'None'}...")

        try:
            updated_state: LegalAgentState = await self.bedrock_client.chat_completions_create(
                response_model=LegalAgentState,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": memory_context + "\n use this memory context to gain idea about the current interaction"},
                    {"role": "user", "content": user_message or "Evaluate the state and dictate the next workflow step."}
                ]
            )
            
            print(f"\n✅ Legal Agent Output:")
            print(f"   New Status: {updated_state.workflow_status}")
            print(f"   Next Question: {updated_state.next_question_for_user[:100] if updated_state.next_question_for_user else 'None'}...")
            print(f"   Drafts to Generate: {len(updated_state.drafts_to_generate)}")
            
        except Exception as e:
            print(f"⚠️ LLM API Error: {e}. Using mock response.")
            print(f"   Keeping current state: {current_state.workflow_status}")
            # Fallback to mock response when API fails
            updated_state = current_state

        session.legal = updated_state

        # Build the exact instruction for the Orchestrator
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)

        # Use the LLM-generated dynamic question when available, otherwise fall back to translations
        if updated_state.workflow_status == WorkflowStatus.AWAITING_DOCS:
            # For initial state, use translation
            response.reply_message = get_translated_response("awaiting_docs", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_USER_INFO:
            # Use the dynamic question generated by the LLM (contextual follow-up)
            if updated_state.next_question_for_user:
                response.reply_message = updated_state.next_question_for_user
            else:
                # Fall back to translation only if LLM didn't generate a question
                response.reply_message = get_translated_response("awaiting_user_info", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_CONSENT:
            # Use dynamic question if available, otherwise use translation
            if updated_state.next_question_for_user:
                response.reply_message = updated_state.next_question_for_user
            else:
                response.reply_message = get_translated_response("awaiting_consent", language)
            
        elif updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT:
            response.reply_message = get_translated_response("ready_to_draft", language)
            
            # FIX: Crucial Orchestrator Handoff!
            # Legal work is done. Hand control back to Orchestrator to decide next steps (e.g. Shelter Agent)
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
        else:
            # Use dynamic message or default
            if updated_state.next_question_for_user:
                response.reply_message = updated_state.next_question_for_user
            else:
                response.reply_message = "I'm here to help with your legal situation. Please tell me more about what you're experiencing."

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