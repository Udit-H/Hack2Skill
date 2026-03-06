from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from models.triage import TriageState
from models.legal import LegalAgentState
from models.shelter import ShelterAgentState
from models.drafting import DraftingAgentState

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator" # Doing initial triage
    TRIAGE = "triage"
    LEGAL = "legal"
    SHELTER = "shelter"
    DRAFTING = "drafting"
    COMPLETED = "completed"

class AgentActionType(str, Enum):
    REPLY_TO_USER = "reply_to_user"           # Wait for user reply
    SWITCH_AGENT = "switch_agent"             # Task done, hand back to orchestrator
    DISPATCH_BACKGROUND = "dispatch_background" # E.g., OCR or PDF generation taking time

class AgentResponse(BaseModel):
    """Every agent must return this exact structure to the Orchestrator."""
    action_type: AgentActionType
    reply_message: Optional[str] = None
    next_active_agent: Optional[AgentType] = None
    background_task_name: Optional[str] = None
    # UI/UX fields for progress tracking and downloads
    progress_status: Optional[str] = None  # e.g., "searching shelters...", "found 3 matches", "drafting doc 1/3"
    is_loading: bool = False  # True when agent is actively processing (for animations)
    error_message: Optional[str] = None  # User-friendly error message if operation fails
    download_urls: Optional[List[str]] = None  # List of generated PDF download URLs

class SessionState(BaseModel):
    """The Global Database Object stored in Redis"""
    session_id: str
    user_phone: Optional[str]
    active_agent: AgentType = Field(default=AgentType.ORCHESTRATOR)
    
    # Sub-States
    triage: Optional[TriageState] = None
    legal: Optional[LegalAgentState] = None
    shelter: Optional[ShelterAgentState] = None
    drafting: Optional[DraftingAgentState] = None
    
    chat_history: List[dict] = Field(default_factory=list, description="Recent message history for context.")
    
    # Cache of last agent response for UI (progress, errors, downloads)
    last_agent_response: Optional[dict] = Field(default=None, description="Latest agent response fields for UI display")