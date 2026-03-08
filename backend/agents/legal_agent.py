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

logger = logging.getLogger(__name__)

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
        # OCR: Only run if we have a document_path AND don't already have extracted text
        # (upload endpoint now does OCR first and stores on state)
        if current_state.extracted_doc_data and not current_state.extracted_doc_data.startswith("OCR failed"):
            logger.info(f"📄 Legal Agent: OCR text already present ({len(current_state.extracted_doc_data)} chars), skipping OCR")
        elif document_path:
            try:
                logger.info(f"📄 Legal Agent: Running OCR on {document_path}")
                ocr_result = await self.ocr_service.analyze(source=document_path)
                extracted = ocr_result.get("content", "")
                if extracted:
                    current_state.extracted_doc_data = extracted
                    logger.info(f"✅ Legal Agent OCR succeeded: {len(extracted)} chars extracted")
                else:
                    current_state.extracted_doc_data = "OCR returned no text."
                    logger.warning(f"⚠️ Legal Agent OCR returned empty text for {document_path}")
            except Exception as e:
                current_state.extracted_doc_data = f"OCR failed: {str(e)}"
                logger.error(f"❌ Legal Agent OCR failed: {e}", exc_info=True)
        else:
            logger.info(f"📄 Legal Agent: No document_path and no existing OCR text")

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

        logger.info(f"\n📋 Legal Agent Input:")
        logger.info(f"   Current Status: {current_state.workflow_status}")
        logger.info(f"   Document Data: {'✅ Present (' + str(len(current_state.extracted_doc_data)) + ' chars)' if current_state.extracted_doc_data else '❌ Missing'}")
        logger.info(f"   Has Consent: {current_state.user_consent_police if current_state.user_consent_police is not None else 'Not set'}")
        logger.info(f"   User Message: {user_message[:100] if user_message else 'None'}...")

        try:
            updated_state: LegalAgentState = await self.llm.create_structured(
                response_model=LegalAgentState,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": memory_context + "\n use this memory context to gain idea about the current interaction"},
                    {"role": "user", "content": user_message or "Evaluate the state and dictate the next workflow step."}
                ]
            )
            
            logger.info(f"\n✅ Legal Agent Output:")
            logger.info(f"   New Status: {updated_state.workflow_status}")
            logger.info(f"   Next Question: {updated_state.next_question_for_user[:100] if updated_state.next_question_for_user else 'None'}...")
            logger.info(f"   Drafts to Generate: {len(updated_state.drafts_to_generate)}")
            
        except Exception as e:
            logger.error(f"⚠️ LLM API Error: {e}. Using mock response.", exc_info=True)
            logger.info(f"   Keeping current state: {current_state.workflow_status}")
            # Fallback to mock response when API fails
            updated_state = current_state

        # ── CRITICAL: Preserve data fields the LLM cannot output ──
        # The LLM returns a new LegalAgentState but extracted_doc_data and
        # retrieved_legal_context are excluded from the schema (too large).
        # We must carry them forward from the previous state.
        if current_state.extracted_doc_data and not updated_state.extracted_doc_data:
            updated_state.extracted_doc_data = current_state.extracted_doc_data
            logger.info(f"   Preserved extracted_doc_data ({len(current_state.extracted_doc_data)} chars)")
        if current_state.retrieved_legal_context and not updated_state.retrieved_legal_context:
            updated_state.retrieved_legal_context = current_state.retrieved_legal_context
            logger.info(f"   Preserved retrieved_legal_context ({len(current_state.retrieved_legal_context)} chars)")

        session.legal = updated_state

        # CODE-LEVEL FALLBACK: If LLM set READY_TO_DRAFT but forgot to populate drafts_to_generate,
        # build them programmatically from triage data (same pattern as shelter agent).
        if (updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT 
            and not updated_state.drafts_to_generate):
            logging.warning("LLM reached READY_TO_DRAFT but drafts_to_generate is empty — building from triage data.")
            
            base_payload = dict(
                applicant_name=triage.victim_name or "Applicant",
                applicant_age=triage.victim_age,
                applicant_phone=triage.victim_phone or "",
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
