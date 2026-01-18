"""LangGraph definition with nodes, edges, and routing logic."""

from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from src.research_assistant.state import ResearchState
from src.research_assistant.nodes import (
    planner_node,
    researcher_node,
    reviewer_node,
    writer_node,
)
from src.research_assistant.persistence import get_checkpointer


# Maximum revision attempts before forced termination
MAX_REVISIONS = 3


def route_after_review(state: ResearchState) -> Literal["researcher", "writer", "force_end"]:
    """
    Router logic for the self-correction loop.
    
    Decision tree:
    1. If revision_count > MAX_REVISIONS -> force_end (safety)
    2. If critique score < 0.8 AND should_refine -> researcher (loop back)
    3. Otherwise -> writer (proceed to synthesis)
    
    Args:
        state: Current graph state with latest_critique and revision_count
        
    Returns:
        Next node to route to
    """
    revision_count = state.get("revision_count", 0)
    critique = state.get("latest_critique")
    
    # Safety: Prevent infinite loops
    if revision_count > MAX_REVISIONS:
        return "force_end"
    
    # Quality check
    if critique:
        if critique.score < 0.8 and critique.should_refine:
            return "researcher"
    
    return "writer"


def should_continue_research(state: ResearchState) -> Literal["researcher", "reviewer"]:
    """
    Check if there are more plan steps to execute.
    
    Args:
        state: Current graph state
        
    Returns:
        "researcher" if more steps remain, "reviewer" if all done
    """
    current_plan = state.get("current_plan", [])
    current_step_idx = state.get("current_step_idx", 0)
    
    if current_step_idx < len(current_plan):
        return "researcher"
    return "reviewer"


def build_graph() -> StateGraph:
    """
    Build the Self-Correcting Research Assistant graph.
    
    Topology:
        START -> Planner -> Researcher (loop for each step) -> Reviewer
        Reviewer -> Router Decision:
            - If score < 0.8: back to Planner (refine) -> Researcher
            - If revision_count > 3: force_end
            - Otherwise: Writer -> END
    
    Returns:
        Configured StateGraph (not compiled)
    """
    graph = StateGraph(ResearchState)
    
    # Add all nodes
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("writer", writer_node)
    
    # Entry point
    graph.add_edge(START, "planner")
    
    # Planner -> Researcher
    graph.add_edge("planner", "researcher")
    
    # Researcher -> Check if more steps or go to reviewer
    graph.add_conditional_edges(
        "researcher",
        should_continue_research,
        {
            "researcher": "researcher",
            "reviewer": "reviewer",
        }
    )
    
    # Reviewer -> Router decision (loop back or proceed)
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "researcher": "planner",  # Go back to planner to refine
            "writer": "writer",
            "force_end": END,
        }
    )
    
    # Writer -> END
    graph.add_edge("writer", END)
    
    return graph


def create_app(
    enable_hitl: bool = True,
    db_path: str | None = None,
) -> CompiledStateGraph:
    """
    Create the compiled graph application with optional HITL breakpoint.
    
    Args:
        enable_hitl: If True, pause before writer node for human review
        db_path: Optional custom database path for persistence
        
    Returns:
        Compiled graph ready for invocation
    """
    graph = build_graph()
    checkpointer = get_checkpointer(db_path)
    
    compile_kwargs = {
        "checkpointer": checkpointer,
    }
    
    if enable_hitl:
        # Pause before writer node for human review
        compile_kwargs["interrupt_before"] = ["writer"]
    
    return graph.compile(**compile_kwargs)


def create_app_without_persistence(enable_hitl: bool = False) -> CompiledStateGraph:
    """
    Create compiled graph without persistence (for testing).
    
    Args:
        enable_hitl: If True, pause before writer node
        
    Returns:
        Compiled graph without checkpointing
    """
    graph = build_graph()
    
    if enable_hitl:
        return graph.compile(interrupt_before=["writer"])
    
    return graph.compile()
