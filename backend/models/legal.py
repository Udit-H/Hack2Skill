from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

# for Delhi only
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class DraftType(str, Enum):
    # Eviction
    POLICE_INTIMATION = "police_intimation"                     # Police complaint (BNS 126)
    CIVIL_INJUNCTION_PETITION = "civil_injunction_petition"     # Civil court injunction
    INTERIM_RELIEF_APPLICATION = "interim_relief_application"   # Interim relief
    # Domestic Violence
    DIR_FORM_1 = "dir_form_1"                                   # Domestic Incident Report
    SECTION_12_PETITION = "section_12_petition"                 # DV Act Section 12
    # Shelter
    SHELTER_REFERRAL = "shelter_referral"                       # Referral to shelter org
    BBMP_SHELTER_REQUEST = "bbmp_shelter_request"               # BBMP shelter request
    NGO_REFERRAL = "ngo_referral"                               # NGO referral letter
    # Senior Citizen
    SENIOR_CITIZEN_TRIBUNAL = "senior_citizen_tribunal"         # 2007 Act tribunal complaint
    # Safety
    SAFETY_PLAN = "safety_plan"                                 # DV safety plan document
    # Legal Aid
    KSLSA_LEGAL_AID = "kslsa_legal_aid"                         # Karnataka State Legal Services

class WorkflowStatus(str, Enum):
    AWAITING_DOCS = "awaiting_docs"
    AWAITING_USER_INFO = "awaiting_user_info"
    AWAITING_CONSENT = "awaiting_consent"
    READY_TO_DRAFT = "ready_to_draft"

class LegalDraftPayload(BaseModel):
    draft_type: DraftType
    applicant_name: str
    applicant_age: Optional[int] = Field(None, description="Age of the applicant")
    applicant_phone: Optional[str] = Field(None, description="Contact phone number of the applicant")
    opponent_name: Optional[str] = None
    property_address: Optional[str] = None
    
    # Delhi DSLSA Specifics
    monthly_income: Optional[int] = Field(None, description="Required for DSLSA form")
    caste_category: Optional[str] = Field(None, description="SC/ST/Women/General - affects DSLSA eligibility")
    
    # Senior Citizen Specifics
    is_property_in_applicant_name: Optional[bool] = None
    
    # Domestic Violence Specifics
    relationship_to_respondent: Optional[str] = Field(None, description="e.g., Husband, Live-in Partner, Father-in-law")
    violence_types: Optional[list[str]] = Field(None, description="e.g., ['physical', 'emotional', 'economic', 'sexual']")
    children_involved: Optional[bool] = Field(None, description="Are minor children affected?")
    number_of_children: Optional[int] = Field(None)
    marriage_date: Optional[str] = Field(None, description="Date of marriage if applicable")
    immediate_danger: Optional[bool] = Field(None, description="Is the user currently in danger?")
    
    # Safety Plan Specifics
    trusted_contact_name: Optional[str] = Field(None)
    trusted_contact_phone: Optional[str] = Field(None)
    safe_location: Optional[str] = Field(None, description="A place the user can go in emergency")
    
    draft_body_summary: str = Field(description="JSON or Text mapping for the specific legal form.")

class LegalAgentState(BaseModel):
    """State managed by the Legal Agent. extracted_doc_data and retrieved_legal_context
    are excluded from the JSON schema so the LLM never tries to output them —
    they're managed by code (OCR endpoint / RAG service)."""
    
    model_config = {
        "json_schema_extra": lambda schema: [
            schema.get("properties", {}).pop(k, None)
            for k in ["extracted_doc_data", "retrieved_legal_context"]
        ]
    }

    internal_plan: list[str] = Field(
        default_factory=list,
        description="MANDATORY FIRST STEP: Before any decision, list your reasoning. "
                    "1) What facts do I already know? 2) What is missing? 3) What should I do next and why?"
    )
    
    workflow_status: WorkflowStatus = WorkflowStatus.AWAITING_DOCS
    
    # These are DATA fields managed by code, NOT by the LLM.
    extracted_doc_data: Optional[str] = Field(None, exclude=True)
    retrieved_legal_context: Optional[str] = Field(None, exclude=True)
    
    next_question_for_user: Optional[str] = Field(None)
    user_consent_police: Optional[bool] = Field(None)
    
    drafts_to_generate: List[LegalDraftPayload] = Field(default_factory=list)

"""
# In general
class DraftType(str, Enum):
    CEASE_AND_DESIST = "cease_and_desist"
    POLICE_INTIMATION = "police_intimation"
    DIR_FORM_1 = "dir_form_1"
    SDM_PETITION = "sdm_petition"
    NALSA_APPLICATION = "nalsa_application"

class WorkflowStatus(str, Enum):
    AWAITING_DOCS = "awaiting_docs"               # Needs rent agreement, medical report, etc.
    AWAITING_USER_INFO = "awaiting_user_info"     # Doc uploaded, but still missing specific details
    AWAITING_CONSENT = "awaiting_consent"         # Ready to draft, but needs permission (e.g. Police)
    READY_TO_DRAFT = "ready_to_draft"             # All data & consent gathered. Generate PDFs.

class LegalDraftPayload(BaseModel):
    draft_type: DraftType
    recipient_authority: str
    applicant_name: str
    opponent_name: Optional[str]
    incident_date_str: str
    property_address: Optional[str]
    applicable_laws_to_cite: List[str]
    draft_body_summary: str

class LegalAgentState(BaseModel):
    workflow_status: WorkflowStatus = Field(description="Strictly dictate what the agent must do next.")
    extracted_doc_data: Optional[str] = Field(None, description="Text extracted from user uploaded files.")
    
    next_question_for_user: Optional[str] = Field(
        None, description="If status is AWAITING_USER_INFO, write the exact question to ask the user here."
    )
    
    user_consent_police: Optional[bool] = Field(None, description="True/False if consent for police draft is given.")
    
    drafts_to_generate: List[LegalDraftPayload] = Field(
        default_factory=list, description="Populate ONLY when status is READY_TO_DRAFT."
    )
"""

