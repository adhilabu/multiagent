"""API routes for research operations."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.research import (
    ResearchRequest,
    ResearchResponse,
    ApprovalRequest,
    SessionResponse,
    CheckpointListResponse,
)
from app.services.research import research_service


router = APIRouter(prefix="/research", tags=["Research"])


@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Research Session",
    description="Start a new research session with the given query. Returns immediately with session info.",
)
async def start_research(request: ResearchRequest) -> ResearchResponse:
    """
    Start a new research session.
    
    - **query**: The research question to investigate
    - **thread_id**: Optional session ID for persistence (auto-generated if not provided)
    - **enable_hitl**: Enable human-in-the-loop breakpoint before final synthesis
    """
    try:
        return research_service.start_research(
            query=request.query,
            thread_id=request.thread_id,
            enable_hitl=request.enable_hitl,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research: {str(e)}"
        )


@router.get(
    "/{thread_id}",
    response_model=SessionResponse,
    summary="Get Session Status",
    description="Get the current status and results of a research session.",
)
async def get_session(thread_id: str) -> SessionResponse:
    """
    Get the current state of a research session.
    
    - **thread_id**: The session thread ID
    """
    session = research_service.get_session(thread_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {thread_id}"
        )
    
    return session


@router.post(
    "/{thread_id}/approve",
    response_model=ResearchResponse,
    summary="Approve HITL Breakpoint",
    description="Approve the research results and continue to final synthesis.",
)
async def approve_session(thread_id: str, request: ApprovalRequest) -> ResearchResponse:
    """
    Approve or provide feedback for HITL breakpoint.
    
    - **thread_id**: The session thread ID
    - **approved**: Whether to approve and continue
    - **feedback**: Optional feedback to incorporate in final synthesis
    """
    # First check if session exists
    session = research_service.get_session(thread_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {thread_id}"
        )
    
    if session.status != "awaiting_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not awaiting approval. Current status: {session.status}"
        )
    
    try:
        return research_service.approve_session(
            thread_id=thread_id,
            approved=request.approved,
            feedback=request.feedback,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve session: {str(e)}"
        )


@router.get(
    "/{thread_id}/checkpoints",
    response_model=CheckpointListResponse,
    summary="List Checkpoints",
    description="List all checkpoints for time-travel debugging.",
)
async def list_checkpoints(thread_id: str) -> CheckpointListResponse:
    """
    List all checkpoints for a research session.
    
    - **thread_id**: The session thread ID
    """
    return research_service.get_checkpoints(thread_id)
