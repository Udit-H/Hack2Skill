from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from enum import Enum

class ShelterWorkflowStatus(str, Enum):
    AWAITING_LOCATION = "awaiting_location"
    AWAITING_USER_DETAILS = "awaiting_user_details"
    SEARCHING_SHELTERS = "searching_shelters"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SHELTER_MATCHED = "shelter_matched"
    FOLLOW_UP = "follow_up"

class GeoLocation(BaseModel):
    latitude: float
    longitude: float

class ShelterProfile(BaseModel):
    shelter_id: int
    name: str
    shelter_type: str = Field(description="This is for the class, gender and age of the person")
    address: str
    contact_number: str
    distance_km: float = Field(description="Calculated distance from user's current location.")
    google_maps_url: str = Field(description="Clickable link for the user to get directions.")
    capacity_available: Optional[bool] = Field(None, description="Whether the shelter has available space")

class ShelterMatchResult(BaseModel):
    status: Literal["success", "failure"]
    nearest_shelters: List[ShelterProfile]
    sms_dispatched_to_manager: bool

class UserShelterProfile(BaseModel):
    """Information about the user seeking shelter"""
    age_group: Optional[str] = Field(None, description="child/adult/senior")
    gender: Optional[str] = Field(None, description="male/female/other")
    has_children: Optional[bool] = None
    has_disabilities: Optional[bool] = None
    needs_medical_attention: Optional[bool] = None
    preferred_duration: Optional[str] = Field(None, description="emergency/short-term/long-term")

class ShelterAgentState(BaseModel):
    """State management for the shelter agent"""
    workflow_status: ShelterWorkflowStatus = Field(default=ShelterWorkflowStatus.AWAITING_LOCATION)
    
    user_location: Optional[GeoLocation] = None
    user_profile: Optional[UserShelterProfile] = Field(default_factory=UserShelterProfile)
    
    next_question_for_user: Optional[str] = None
    
    matched_shelters: List[ShelterProfile] = Field(default_factory=list)
    selected_shelter: Optional[ShelterProfile] = None
    
    urgency_level: Optional[str] = Field(None, description="immediate/moderate/planning")
    special_requirements: Optional[str] = Field(None, description="Any special needs or requirements") 