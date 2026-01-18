"""Researcher Node - Executes Tavily search for plan steps."""

import os
from typing import Any

from langchain_community.tools.tavily_search import TavilySearchResults

from src.research_assistant.state import ResearchState, ResearchResult


def get_tavily_tool() -> TavilySearchResults:
    """Initialize Tavily search tool."""
    return TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
    )


def researcher_node(state: ResearchState) -> dict[str, Any]:
    """
    Researcher Node: Execute Tavily search for the current plan step.
    
    This node takes the current step from the plan and executes
    a web search using Tavily, then stores the results in
    gathered_context.
    
    Args:
        state: Current graph state with current_plan and current_step_idx
        
    Returns:
        Updated state with new research results appended
    """
    current_plan = state.get("current_plan", [])
    current_step_idx = state.get("current_step_idx", 0)
    gathered_context = list(state.get("gathered_context", []))
    
    # Safety check
    if not current_plan or current_step_idx >= len(current_plan):
        return {"gathered_context": gathered_context}
    
    current_step = current_plan[current_step_idx]
    search_query = current_step.search_query or current_step.task
    
    # Execute Tavily search
    tavily = get_tavily_tool()
    
    try:
        search_results = tavily.invoke({"query": search_query})
        
        # Parse results
        findings = []
        sources = []
        
        if isinstance(search_results, list):
            for result in search_results:
                if isinstance(result, dict):
                    content = result.get("content", "")
                    url = result.get("url", "")
                    if content:
                        findings.append(content)
                    if url:
                        sources.append(url)
        elif isinstance(search_results, str):
            findings.append(search_results)
        
        research_result = ResearchResult(
            step_id=current_step.step_id,
            query=search_query,
            results=findings,
            sources=sources,
            relevance_score=0.0  # Will be set by reviewer
        )
        
    except Exception as e:
        # Handle search failures gracefully
        research_result = ResearchResult(
            step_id=current_step.step_id,
            query=search_query,
            results=[f"Search failed: {str(e)}"],
            sources=[],
            relevance_score=0.0
        )
    
    # Update step status
    updated_plan = []
    for i, step in enumerate(current_plan):
        if i == current_step_idx:
            updated_step = step.model_copy(update={"status": "completed"})
            updated_plan.append(updated_step)
        else:
            updated_plan.append(step)
    
    gathered_context.append(research_result)
    
    # Move to next step
    next_step_idx = current_step_idx + 1
    
    return {
        "current_plan": updated_plan,
        "current_step_idx": next_step_idx,
        "gathered_context": gathered_context,
    }
