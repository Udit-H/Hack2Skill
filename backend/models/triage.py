from pydantic import BaseModel, Field
from typing import Optional, List
from models.enums import CrisisCategory

class TriageState(BaseModel):
    category: CrisisCategory = Field(description="Categorize the crisis.")
    urgency_level: int = Field(description="1 to 5 scale. 5 means imminent physical danger or currently on the street.")
    
    victim_name: Optional[str] = Field(None, description="Name of the person in distress")
    aggressor_name: Optional[str] = Field(None, description="Name of landlord, abusive spouse, or abusive child. Leave Null for Natural Disasters.")
    
    # Universal Triggers for Track B (Shelter)
    needs_immediate_shelter: bool = Field(description="True if the user has no safe place to sleep tonight (Evicted, Flooded, or Fleeing Abuse).")
    physical_danger_present: bool = Field(description="True if there is active violence, threats, or severe disaster conditions.")
    
    # Case-Specific Flags (LLM sets to True only if explicitly mentioned)
    incident_summary: str = Field(description="A 1-2 sentence factual summary of the user's situation.")
    property_address: Optional[str] = Field(None, description="Address of the disputed or unsafe property.")
    
    has_ownership_claim: Optional[bool] = Field(default=None, description="True if the user claims they own the property (Crucial for Senior Citizen case).")
    is_financially_destitute: Optional[bool] = Field(default=None, description="True if user explicitly states they have no money to pay rent/fees (Crucial for Case 5 - NALSA Aid).")

    missing_info: List[str] = Field(
        default_factory=list,
        description="List of questions to ask to complete this profile based on the category. Keep empty if ready."
    )