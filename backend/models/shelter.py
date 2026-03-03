from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ShelterWorkflowStatus(str, Enum):
    AWAITING_LOCATION = "awaiting_location"
    AWAITING_PREFERENCES = "awaiting_preferences"       # Asking: "Do you need a women-only space or general?"
    AWAITING_SELECTION = "awaiting_selection"           # We showed options, waiting for user to pick 1 or 2
    AWAITING_CONSENT = "awaiting_consent"               # Asking: "Can I send your name to Shelter X?"
    COMPLETED = "completed"

class ShelterProfile(BaseModel):
    shelter_id: int
    name: str
    shelter_type: str 
    address: str
    contact_number: Optional[str] = None
    distance_km: Optional[float] = None
    google_maps_url: str

class ShelterAgentState(BaseModel):
    workflow_status: ShelterWorkflowStatus = ShelterWorkflowStatus.AWAITING_LOCATION
    
    user_location_text: Optional[str] = Field(None, description="City, area, or pin provided by user.")
    user_coordinates: Optional[dict] = Field(None, description="{'lat': float, 'lng': float}")
    
    user_preferences: Optional[str] = Field(None, description="e.g., 'Women-only', 'Family friendly', 'Pet friendly'")
    user_consent_to_share: Optional[bool] = Field(None)
    trigger_new_db_search: bool = Field(
        default=False, 
        description="Set to TRUE if the user just provided location/preferences for the first time, OR if they changed their preferences and we need to fetch new shelters."
    )

    free_shelter_needed: Optional[bool] = Field(default=False, description="Flag which determines whether the user need free shelter or paid")
    selected_shelter_ids: Optional[List[int]] = Field(default_factory=list, description="Shelters the user picked.")
    matched_shelters: List[ShelterProfile] = Field(default_factory=list)
    next_question_for_user: Optional[str] = Field(None)