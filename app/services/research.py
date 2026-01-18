"""Research service wrapping LangGraph logic."""

import uuid
from typing import Optional

from src.research_assistant.state import create_initial_state, ResearchResult, CritiqueResult
from src.research_assistant.graph import create_app
from src.research_assistant.persistence import list_checkpoints, get_checkpoint_state

from app.schemas.research import (
    ResearchResponse,
    ResearchResultItem,
    CritiqueInfo,
    SessionResponse,
    CheckpointItem,
    CheckpointListResponse,
)


class ResearchService:
    """Service class wrapping LangGraph research assistant logic."""
    
    @staticmethod
    def _convert_research_results(results: list[ResearchResult]) -> list[ResearchResultItem]:
        """Convert internal ResearchResult to API schema."""
        return [
            ResearchResultItem(
                step_id=r.step_id,
                query=r.query,
                results=r.results,
                sources=r.sources,
            )
            for r in results
        ]
    
    @staticmethod
    def _convert_critique(critique: Optional[CritiqueResult]) -> Optional[CritiqueInfo]:
        """Convert internal CritiqueResult to API schema."""
        if not critique:
            return None
        return CritiqueInfo(
            score=critique.score,
            feedback=critique.feedback,
            suggestions=critique.suggestions,
            should_refine=critique.should_refine,
        )
    
    @staticmethod
    def _determine_status(state: dict) -> str:
        """Determine the current status based on state."""
        if state.get("final_response"):
            return "completed"
        if state.get("latest_critique") and not state.get("human_approved"):
            return "awaiting_approval"
        if state.get("current_plan"):
            return "researching"
        return "pending"
    
    def start_research(
        self,
        query: str,
        thread_id: Optional[str] = None,
        enable_hitl: bool = True
    ) -> ResearchResponse:
        """
        Start a new research session.
        
        Args:
            query: The research query
            thread_id: Optional thread ID for persistence
            enable_hitl: Whether to enable HITL breakpoint
            
        Returns:
            ResearchResponse with session info and results
        """
        # Generate thread ID if not provided
        if not thread_id:
            thread_id = str(uuid.uuid4())[:8]
        
        # Create the app and initial state
        app = create_app(enable_hitl=enable_hitl)
        initial_state = create_initial_state(query)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the graph
        result = app.invoke(initial_state, config=config)
        
        # Determine status and build response
        status = self._determine_status(result)
        
        # Build message based on status
        if status == "completed":
            message = "Research completed successfully"
        elif status == "awaiting_approval":
            message = "Research ready for human review. Call approve endpoint to continue."
        else:
            message = "Research in progress"
        
        return ResearchResponse(
            thread_id=thread_id,
            status=status,
            message=message,
            gathered_results=self._convert_research_results(result.get("gathered_context", [])),
            critique=self._convert_critique(result.get("latest_critique")),
            final_response=result.get("final_response"),
            revision_count=result.get("revision_count", 0),
        )
    
    def get_session(self, thread_id: str) -> Optional[SessionResponse]:
        """
        Get the current state of a research session.
        
        Args:
            thread_id: The session thread ID
            
        Returns:
            SessionResponse with full session state, or None if not found
        """
        state = get_checkpoint_state(thread_id)
        
        if not state:
            return None
        
        return SessionResponse(
            thread_id=thread_id,
            user_query=state.get("user_query", ""),
            status=self._determine_status(state),
            gathered_results=self._convert_research_results(state.get("gathered_context", [])),
            critique=self._convert_critique(state.get("latest_critique")),
            revision_count=state.get("revision_count", 0),
            human_approved=state.get("human_approved", False),
            final_response=state.get("final_response"),
        )
    
    def approve_session(
        self,
        thread_id: str,
        approved: bool = True,
        feedback: Optional[str] = None
    ) -> ResearchResponse:
        """
        Approve or provide feedback for HITL breakpoint.
        
        Args:
            thread_id: The session thread ID
            approved: Whether to approve and continue
            feedback: Optional feedback to incorporate
            
        Returns:
            ResearchResponse with updated status
        """
        if not approved:
            return ResearchResponse(
                thread_id=thread_id,
                status="rejected",
                message="Research session rejected by user",
            )
        
        # Create app and continue execution
        app = create_app(enable_hitl=True)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Build continuation state
        continuation = {"human_approved": True}
        if feedback:
            continuation["human_feedback"] = feedback
        
        # Continue from breakpoint
        result = app.invoke(continuation, config=config)
        
        return ResearchResponse(
            thread_id=thread_id,
            status=self._determine_status(result),
            message="Research completed after approval" if result.get("final_response") else "Research continuing",
            gathered_results=self._convert_research_results(result.get("gathered_context", [])),
            critique=self._convert_critique(result.get("latest_critique")),
            final_response=result.get("final_response"),
            revision_count=result.get("revision_count", 0),
        )
    
    def get_checkpoints(self, thread_id: str) -> CheckpointListResponse:
        """
        List all checkpoints for a session.
        
        Args:
            thread_id: The session thread ID
            
        Returns:
            CheckpointListResponse with list of checkpoints
        """
        checkpoints = list_checkpoints(thread_id)
        
        return CheckpointListResponse(
            thread_id=thread_id,
            checkpoints=[
                CheckpointItem(
                    checkpoint_id=cp.get("checkpoint_id", ""),
                    metadata=cp.get("metadata"),
                )
                for cp in checkpoints
            ],
        )


# Singleton instance
research_service = ResearchService()
