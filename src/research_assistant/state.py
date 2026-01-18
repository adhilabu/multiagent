"""State definitions for the Self-Correcting Research Assistant."""

from typing import TypedDict, Annotated, Sequence, Optional, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """Individual step in the research plan."""
    
    step_id: int = Field(description="Unique identifier for the step")
    task: str = Field(description="Description of the sub-task")
    status: str = Field(
        default="pending",
        description="Status: pending | in_progress | completed | failed"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Tavily search query for this step"
    )


class ResearchResult(BaseModel):
    """Result from a single research step."""
    
    step_id: int = Field(description="Which plan step this result belongs to")
    query: str = Field(description="The search query used")
    results: List[str] = Field(
        default_factory=list,
        description="List of relevant findings"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="URLs of sources"
    )
    relevance_score: float = Field(
        default=0.0,
        description="Reviewer's relevance score (0-1)"
    )


class CritiqueResult(BaseModel):
    """Reviewer's evaluation of research results."""
    
    score: float = Field(description="Overall critique score (0-1)")
    feedback: str = Field(description="Detailed feedback on the research quality")
    suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for improvement"
    )
    should_refine: bool = Field(
        default=False,
        description="Whether to refine and retry"
    )


class ResearchState(TypedDict):
    """
    Main state object for the Self-Correcting Research Assistant.
    
    This state flows through all nodes and captures the complete
    research lifecycle from planning to final synthesis.
    
    Attributes:
        messages: Chat history with user and system messages
        user_query: The original query from the user
        current_plan: List of plan steps to execute
        current_step_idx: Index of the currently executing step
        gathered_context: Research results collected so far
        latest_critique: Most recent reviewer evaluation
        revision_count: Number of refinement iterations (max: 3)
        human_approved: Whether human has approved results
        human_feedback: Optional feedback from human review
        final_response: The synthesized final answer
    """
    
    # Core conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # User's original query
    user_query: str
    
    # Planning
    current_plan: List[PlanStep]
    current_step_idx: int
    
    # Research results
    gathered_context: List[ResearchResult]
    
    # Review & Self-correction
    latest_critique: Optional[CritiqueResult]
    revision_count: int
    
    # Human-in-the-loop
    human_approved: bool
    human_feedback: Optional[str]
    
    # Final output
    final_response: Optional[str]


def create_initial_state(user_query: str) -> dict:
    """
    Create an initial state for a new research session.
    
    Args:
        user_query: The user's research question
        
    Returns:
        Initial state dictionary ready for the graph
    """
    return {
        "messages": [],
        "user_query": user_query,
        "current_plan": [],
        "current_step_idx": 0,
        "gathered_context": [],
        "latest_critique": None,
        "revision_count": 0,
        "human_approved": False,
        "human_feedback": None,
        "final_response": None,
    }
