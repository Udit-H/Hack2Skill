from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from models.enums import CrisisCategory # Assuming you have this (e.g., ILLEGAL_EVICTION, DOMESTIC_VIOLENCE)

class TriageWorkflowStatus(str, Enum):
    GREETING = "greeting"                       # Explaining the app, asking what happened
    GATHERING_FACTS = "gathering_facts"         # Figuring out ownership/financial status
    ASSESSING_NEEDS = "assessing_needs"         # Asking explicitly for Shelter and Legal intent
    COMPLETED = "completed"                     # Profiling done, ready to hand off

class TriageState(BaseModel):
    internal_plan: list[str] = Field(
        default_factory=list,
        description="MANDATORY FIRST STEP: Before any decision, list your reasoning. "
                    "1) What facts do I already know? 2) What is missing? 3) What should I do next and why?"
    )
    
    workflow_status: TriageWorkflowStatus = Field(default=TriageWorkflowStatus.GREETING)
    
    category: Optional[CrisisCategory] = Field(None, description="The broad category of the crisis.")
    urgency_level: Optional[int] = Field(None, description="Scale of 1-5. 5 means physically locked out/in danger.")
    incident_summary: Optional[str] = Field(None, description="A 2-sentence summary of who the user is and what happened.")
    
    victim_name: Optional[str] = Field(None, description="Name of the person in distress")
    aggressor_name: Optional[str] = Field(None, description="Name of landlord, abusive spouse, or abusive child. Leave Null for Natural Disasters.")
    property_address: Optional[str] = Field(None, description="Address of the disputed or unsafe property.")

    eviction_reason: Optional[str] = Field(None, description="Why did the landlord/family kick them out?")
    has_ownership_claim: Optional[bool] = Field(None, description="Does the user claim to legally own the property?")
    is_financially_destitute: Optional[bool] = Field(None, description="Are they unable to afford a lawyer/rent?")
    
    needs_immediate_shelter: Optional[bool] = Field(None, description="True if they want us to find a shelter.")
    needs_legal_action: Optional[bool] = Field(None, description="True if they consent to drafting legal documents/police intimations.")
    
    next_question_for_user: Optional[str] = Field(None, description="The exact message to reply to the user.")