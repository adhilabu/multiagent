"""Pydantic schemas for API request/response models."""

from typing import Optional, List
from pydantic import BaseModel, Field


# ============ Request Models ============

class ResearchRequest(BaseModel):
    """Request model for starting a new research session."""
    
    query: str = Field(
        ...,
        description="The research query to investigate",
        min_length=3,
        max_length=1000,
        json_schema_extra={"example": "What are the latest advancements in LangGraph?"}
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for session persistence. Auto-generated if not provided.",
        json_schema_extra={"example": "abc12345"}
    )
    enable_hitl: bool = Field(
        default=True,
        description="Enable human-in-the-loop breakpoint before final synthesis"
    )


class ApprovalRequest(BaseModel):
    """Request model for approving HITL breakpoint."""
    
    approved: bool = Field(
        default=True,
        description="Whether to approve and continue"
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Optional feedback to incorporate in final synthesis",
        json_schema_extra={"example": "Focus more on practical applications"}
    )


# ============ Response Models ============

class ResearchResultItem(BaseModel):
    """Individual research result from a step."""
    
    step_id: int
    query: str
    results: List[str]
    sources: List[str]


class CritiqueInfo(BaseModel):
    """Critique information from the reviewer."""
    
    score: float = Field(ge=0, le=1)
    feedback: str
    suggestions: List[str]
    should_refine: bool


class ResearchResponse(BaseModel):
    """Response model for research operations."""
    
    thread_id: str = Field(description="Session thread ID for resuming/checking status")
    status: str = Field(
        description="Current status: pending | researching | awaiting_approval | completed | failed"
    )
    message: str = Field(description="Human-readable status message")
    
    # Optional fields based on progress
    gathered_results: Optional[List[ResearchResultItem]] = None
    critique: Optional[CritiqueInfo] = None
    final_response: Optional[str] = None
    revision_count: int = 0


class SessionResponse(BaseModel):
    """Full session state response."""
    
    thread_id: str
    user_query: str
    status: str
    gathered_results: List[ResearchResultItem]
    critique: Optional[CritiqueInfo] = None
    revision_count: int
    human_approved: bool
    final_response: Optional[str] = None


class CheckpointItem(BaseModel):
    """Individual checkpoint info."""
    
    checkpoint_id: str
    metadata: Optional[dict] = None


class CheckpointListResponse(BaseModel):
    """Response for listing checkpoints."""
    
    thread_id: str
    checkpoints: List[CheckpointItem]


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str
    app_name: str
