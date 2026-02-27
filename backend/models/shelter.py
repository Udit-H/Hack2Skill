from pydantic import BaseModel, Field
from typing import Optional, Literal

class GeoLocation(BaseModel):
    latitude: float
    longitude: float

class ShelterProfile(BaseModel):
    shelter_id: int
    name: str
    shelter_type: str = Field(description="This is for the class, gender and age of the person")
    address: str
    contact_number: str
    distance_km: float = Field(description="Calculated distance from user's current WhatsApp pin.")
    google_maps_url: str = Field(description="Clickable link for the user to get directions.")

class ShelterMatchResult(BaseModel):
    status: Literal["success", "Failure"]
    nearest_shelters: list[ShelterProfile]
    sms_dispatched_to_manager: bool 