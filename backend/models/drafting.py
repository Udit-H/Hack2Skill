from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class DraftingWorkflowStatus(str, Enum):
    PENDING = "pending"           # Waiting for upstream agents to finish
    GENERATING = "generating"     # Actively rendering PDFs
    COMPLETED = "completed"       # All PDFs generated
    FAILED = "failed"             # Generation failed


class GeneratedDraft(BaseModel):
    """A single generated PDF document."""
    draft_type: str = Field(description="Type of draft, e.g. 'police_intimation'")
    title: str = Field(description="Human-readable title, e.g. 'Police Complaint (BNS 126)'")
    filename: str = Field(description="File on disk, e.g. 'police_intimation_john.pdf'")
    download_url: str = Field(description="API URL to download, e.g. '/api/drafts/s-abc/file.pdf'")


class DraftingAgentState(BaseModel):
    workflow_status: DraftingWorkflowStatus = DraftingWorkflowStatus.PENDING
    generated_drafts: List[GeneratedDraft] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
