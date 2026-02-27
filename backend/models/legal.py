from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

# for Delhi only
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class DraftType(str, Enum):
    DELHI_SHO_INTIMATION = "delhi_sho_intimation"           # Case 1
    DIR_FORM_1 = "dir_form_1"                               # Case 2
    DELHI_DM_EVICTION_PETITION = "delhi_dm_eviction_petition" # Case 3
    DSLSA_LEGAL_AID_FORM = "dslsa_legal_aid_form"           # Case 5

class WorkflowStatus(str, Enum):
    AWAITING_DOCS = "awaiting_docs"
    AWAITING_USER_INFO = "awaiting_user_info"
    AWAITING_CONSENT = "awaiting_consent"
    READY_TO_DRAFT = "ready_to_draft"

class LegalDraftPayload(BaseModel):
    draft_type: DraftType
    applicant_name: str
    opponent_name: Optional[str]
    property_address: Optional[str]
    
    # Delhi DSLSA Specifics
    monthly_income: Optional[int] = Field(None, description="Required for DSLSA form")
    caste_category: Optional[str] = Field(None, description="SC/ST/Women/General - affects DSLSA eligibility")
    
    # Senior Citizen Specifics
    is_property_in_applicant_name: Optional[bool] = None
    
    draft_body_summary: str = Field(description="JSON or Text mapping for the specific legal form.")

class LegalAgentState(BaseModel):
    workflow_status: WorkflowStatus
    extracted_doc_data: Optional[str] = Field(None, description="Raw OCR text.")
    retrieved_legal_context: Optional[str] = Field(None, description="Delhi laws from RAGFlow.")
    
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

