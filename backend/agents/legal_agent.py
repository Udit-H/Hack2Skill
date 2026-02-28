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

# Translations for agent responses
AGENT_RESPONSES = {
    "en": {
        "awaiting_docs": "Please upload a clear photo of your rent agreement, eviction notice, or ID card so I can extract your details automatically.",
        "awaiting_user_info": "What is your current situation regarding the eviction? Please describe the details.",
        "awaiting_consent": "Filing a Police Intimation can escalate matters. Do I have your explicit permission to draft an intimation to the Delhi SHO regarding Wrongful Restraint?",
        "ready_to_draft": "I have successfully mapped your data to the official Delhi legal forms. The system will now generate your documents.",
        "default": "I'm here to help with your legal situation. Please tell me more about what you're experiencing.",
    },
    "hi": {
        "awaiting_docs": "कृपया अपने किराया समझौते, बेदखली नोटिस, या ID कार्ड की स्पष्ट तस्वीर अपलोड करें ताकि मैं आपके विवरण को स्वचालित रूप से निकाल सकूँ।",
        "awaiting_user_info": "बेदखली के संबंध में आपकी वर्तमान स्थिति क्या है? कृपया विवरण बताएं।",
        "awaiting_consent": "पुलिस सूचना दाखिल करने से मामला गंभीर हो सकता है। क्या मेरे पास दिल्ली SHO को अनुचित रोक के बारे में एक सूचना तैयार करने की आपकी स्पष्ट अनुमति है?",
        "ready_to_draft": "मैंने आपके डेटा को आधिकारिक दिल्ली कानूनी फॉर्मों से सफलतापूर्वक मैप किया है। सिस्टम अब आपके दस्तावेज़ तैयार करेगा।",
        "default": "मैं आपकी कानूनी स्थिति के साथ आपकी मदद करने के लिए यहाँ हूँ। कृपया बताएं कि आप क्या अनुभव कर रहे हैं।",
    },
    "ta": {
        "awaiting_docs": "உங்கள் வாடை ஒப்பந்தம், வெளியேற்றல் நோட்டீஸ் அல்லது ID கார்டின் தெளிவான புகைப்படத்தை அपलोड் செய்கிறை எனது உங்கள் விவரங்களை தானாக பிரித்தெடுக்கலாம்.",
        "awaiting_user_info": "வெளியேற்றலைப் பொறுத்து உங்கள் தற்போதைய நிலை என்ன? கृपया விவரங்களை விவரிக்கவும்.",
        "awaiting_consent": "போலீஸ் அறிவுரையை தாக்கல் செய்வது விஷயத்தை அதிகாரம் செய்யலாம். டெல்லி SHO க்கு தவறான கட்டுப்பாடு குறித்து அறிவுரையை வசரிக்க உங்கள் வெளிப்படையான அனுமதி உள்ளது கதா?",
        "ready_to_draft": "நான் உங்கள் தரவை உத்திய டெல்லி சட்ட வடிவங்களுடன் வெற்றிகரமாக மாற்றியுள்ளேன். கணினி இப்போது உங்கள் ஆவணங்களை உருவாக்கும்.",
        "default": "நான் உங்கள் சட்ட நிலைமையுடன் உங்களுக்கு உதவ இங்கே இருக்கிறேன். நீங்கள் என்ன அனுபவிக்கிறீர்கள் என்பது பற்றி கூறவும்.",
    },
    "bn": {
        "awaiting_docs": "আপনার ভাড়া চুক্তি, উচ্ছেদ বিজ্ঞপ্তি বা আইডি কার্ডের একটি পরিষ্কার ফটো আপলোড করুন যাতে আমি আপনার বিবরণ স্বয়ংক্রিয়ভাবে বের করতে পারি।",
        "awaiting_user_info": "উচ্ছেদের বিষয়ে আপনার বর্তমান পরিস্থিতি কী? অনুগ্রহ করে বিবরণ বলুন।",
        "awaiting_consent": "পুলিশ অবহিতকরণ ফাইল করা বিষয়টি বাড়াতে পারে। আমার কাছে দিল্লি SHO এর কাছে অনুচিত বিধিনিষেধ সম্পর্কে একটি অবহিতকরণ তৈরি করার জন্য আপনার স্পষ্ট অনুমতি আছে?",
        "ready_to_draft": "আমি আপনার ডেটাকে আধিকারিক দিল্লি আইনি ফর্মগুলিতে সফলভাবে ম্যাপ করেছি। সিস্টেম এখন আপনার নথি তৈরি করবে।",
        "default": "আমি আপনার আইনি পরিস্থিতিতে আপনাকে সাহায্য করতে এখানে আছি। অনুগ্রহ করে বলুন আপনি কী অনুভব করছেন।",
    }
}

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
    
    def get_translated_response(self, response_key: str, language: str = "en") -> str:
        """Get a translated response message based on workflow status and language."""
        lang_responses = AGENT_RESPONSES.get(language, AGENT_RESPONSES["en"])
        return lang_responses.get(response_key, lang_responses.get("default", "I'm here to help."))
    
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

        try:
            updated_state: LegalAgentState = await self.client.chat.completions.create(
                model="gemini-2.5-flash", 
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

        # Build the exact instruction for the Orchestrator
        response = AgentResponse(action_type=AgentActionType.REPLY_TO_USER)

        # Map workflow status to response keys for translation
        status_key = updated_state.workflow_status.value if updated_state.workflow_status else "default"
        status_key = status_key.lower()  # Normalize to lowercase

        if updated_state.workflow_status == WorkflowStatus.AWAITING_DOCS:
            response.reply_message = self.get_translated_response("awaiting_docs", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_USER_INFO:
            response.reply_message = self.get_translated_response("awaiting_user_info", language)
            
        elif updated_state.workflow_status == WorkflowStatus.AWAITING_CONSENT:
            response.reply_message = self.get_translated_response("awaiting_consent", language)
            
        elif updated_state.workflow_status == WorkflowStatus.READY_TO_DRAFT:
            response.reply_message = self.get_translated_response("ready_to_draft", language)
            
            # FIX: Crucial Orchestrator Handoff!
            # Legal work is done. Hand control back to Orchestrator to decide next steps (e.g. Shelter Agent)
            response.action_type = AgentActionType.SWITCH_AGENT
            response.next_active_agent = AgentType.ORCHESTRATOR
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