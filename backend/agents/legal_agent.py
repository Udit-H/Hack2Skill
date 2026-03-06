import os
import logging
import jinja2

from config.translations import get_translated_response
from models.enums import CrisisCategory
from models.legal import LegalAgentState, WorkflowStatus, LegalDraftPayload, DraftType
from models.triage import TriageState
from models.session import SessionState, AgentResponse, AgentActionType, AgentType # FIX: Added Global States
from services.llm_service import LLMService
from services.rag_service import RAGService
from services.ocr_service import DocumentIntelligenceService 

# Remove this line later
from core.memory import MemoryManager

class LegalAgent:
    def __init__(self):
        self.llm = LLMService()
        
        self.ocr_service = DocumentIntelligenceService()
        self.rag_service = RAGService()
        
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

        # RAG (synchronous — uses sync Cohere + ChromaDB clients)
        if not current_state.retrieved_legal_context:
            rag_query = f"Laws regarding {triage.category.value}: {triage.incident_summary}"
            response = self.rag_service.search(rag_query)
            current_state.retrieved_legal_context = response.answer

        # --- PHASE 2: SELECT PROMPT BY CRISIS CATEGORY ---
        category = triage.category
        if category == CrisisCategory.DOMESTIC_VIOLENCE:
            template = self.template_env.get_template("legal_agent_dv_system.j2")
        elif category == CrisisCategory.SENIOR_CITIZEN_NEGLECT:
            template = self.template_env.get_template("legal_agent_senior_system.j2")
        else:
            # Default: eviction / unclear / natural disaster
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
        session: SessionState, 
        memory_manager, 
        user_message: str = None, 
        document_path: str = None,
        language: str = "en",
    ) -> AgentResponse: 
        """
        The main asynchronous entry point. Orchestrates the workflow.
        """

        triage = session.triage

        # Initialize Legal state if it doesn't exist yet
        if not session.legal:
            session.legal = LegalAgentState()
            
        current_state = session.legal

        memory_context = memory_manager.get_memory_context()

        system_prompt = await self.get_legal_system_prompt(triage, current_state, document_path)

        try:
            updated_state: LegalAgentState = await self.llm.create_structured(
                response_model=LegalAgentState,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content":memory_context + "\n use this memory context to gain idea about the current interaction"},
                    {"role": "user", "content": user_message or "Evaluate the state and dictate the next workflow step."}
                ]
            )
        except Exception as e:
            print(f"⚠️ LLM API Error: {e}. Using mock response.")
            # Fallback to mock response when API fails
            updated_state = current_state

        session.legal = updated_state

        # CODE-LEVEL FALLBACK: If LLM set READY_TO_DRAFT but forgot to populate drafts_to_generate,
        # build them programmatically from triage data (same pattern as shelter agent).
        if (updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT 
            and not updated_state.drafts_to_generate):
            logging.warning("LLM reached READY_TO_DRAFT but drafts_to_generate is empty — building from triage data.")
            
            base_payload = dict(
                applicant_name=triage.victim_name or "Applicant",
                opponent_name=triage.aggressor_name,
                property_address=triage.property_address,
                monthly_income=0,
                caste_category="General",
                draft_body_summary=triage.incident_summary or "Details to be provided.",
            )

            category = triage.category
            drafts = []

            if category == CrisisCategory.ILLEGAL_EVICTION:
                if updated_state.user_consent_police:
                    drafts.append(LegalDraftPayload(draft_type=DraftType.POLICE_INTIMATION, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.CIVIL_INJUNCTION_PETITION, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.KSLSA_LEGAL_AID, **base_payload))

            elif category == CrisisCategory.DOMESTIC_VIOLENCE:
                drafts.append(LegalDraftPayload(draft_type=DraftType.SAFETY_PLAN, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.DIR_FORM_1, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.SECTION_12_PETITION, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.KSLSA_LEGAL_AID, **base_payload))

            elif category == CrisisCategory.SENIOR_CITIZEN_NEGLECT:
                drafts.append(LegalDraftPayload(draft_type=DraftType.SENIOR_CITIZEN_TRIBUNAL, **base_payload))
                drafts.append(LegalDraftPayload(draft_type=DraftType.KSLSA_LEGAL_AID, **base_payload))
                if updated_state.user_consent_police:
                    drafts.append(LegalDraftPayload(draft_type=DraftType.POLICE_INTIMATION, **base_payload))
            else:
                # Fallback: at least generate legal aid application
                drafts.append(LegalDraftPayload(draft_type=DraftType.KSLSA_LEGAL_AID, **base_payload))

            updated_state.drafts_to_generate = drafts
            session.legal = updated_state
            logging.info(f"Built {len(drafts)} draft payloads from triage data.")

        # Build the exact instruction for the Orchestrator
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)

        # Prefer LLM's contextual response, fall back to static translation
        llm_reply = updated_state.next_question_for_user

        if updated_state.workflow_status == WorkflowStatus.AWAITING_DOCS:
            response.reply_message = llm_reply or get_translated_response("awaiting_docs", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_USER_INFO:
            response.reply_message = llm_reply or get_translated_response("awaiting_user_info", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_CONSENT:
            response.reply_message = llm_reply or get_translated_response("awaiting_consent", language)
            
        elif updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT:
            response.reply_message = llm_reply or get_translated_response("ready_to_draft", language)
            
            # FIX: Crucial Orchestrator Handoff!
            # Legal work is done. Hand control back to Orchestrator to decide next steps (e.g. Shelter Agent)
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
        else:
            response.reply_message = llm_reply or "I'm here to help with your legal situation. Please tell me more about what you're experiencing."

        return response
