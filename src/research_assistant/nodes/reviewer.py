"""Reviewer Node - Evaluates research quality and decides on refinement."""

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.research_assistant.state import ResearchState, CritiqueResult


REVIEWER_SYSTEM_PROMPT = """You are a research quality evaluator. Your task is to assess whether the gathered research adequately answers the user's query.

Evaluate based on:
1. RELEVANCE: Do the results directly address the query?
2. COMPLETENESS: Are all aspects of the query covered?
3. QUALITY: Are the sources credible and information accurate?
4. DEPTH: Is there sufficient detail to provide a comprehensive answer?

Provide your evaluation in this EXACT format:
SCORE: [0.0 to 1.0]
FEEDBACK: [Your detailed assessment]
SUGGESTIONS: [Comma-separated list of improvements needed, or "None" if score >= 0.8]
SHOULD_REFINE: [YES or NO]

A score of 0.8 or higher means the research is sufficient.
Below 0.8 means refinement is needed."""


def get_llm() -> ChatOpenAI:
    """Initialize the LLM for review."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
    )


def parse_critique_response(response: str) -> CritiqueResult:
    """Parse the LLM response into a CritiqueResult."""
    lines = response.strip().split("\n")
    
    score = 0.5
    feedback = ""
    suggestions = []
    should_refine = True
    
    for line in lines:
        line = line.strip()
        upper_line = line.upper()
        
        if upper_line.startswith("SCORE:"):
            try:
                score_str = line.split(":", 1)[1].strip()
                # Handle various formats like "0.8", "0.8/1.0", "80%"
                score_str = score_str.replace("%", "").split("/")[0].strip()
                score = float(score_str)
                if score > 1.0:
                    score = score / 100.0  # Convert percentage
                score = max(0.0, min(1.0, score))
            except (ValueError, IndexError):
                score = 0.5
                
        elif upper_line.startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip() if ":" in line else ""
            
        elif upper_line.startswith("SUGGESTIONS:"):
            suggestions_str = line.split(":", 1)[1].strip() if ":" in line else ""
            if suggestions_str.upper() != "NONE":
                suggestions = [s.strip() for s in suggestions_str.split(",") if s.strip()]
                
        elif upper_line.startswith("SHOULD_REFINE:"):
            refine_str = line.split(":", 1)[1].strip().upper() if ":" in line else ""
            should_refine = refine_str == "YES"
    
    return CritiqueResult(
        score=score,
        feedback=feedback or "No detailed feedback provided.",
        suggestions=suggestions,
        should_refine=should_refine or score < 0.8
    )


def reviewer_node(state: ResearchState) -> dict[str, Any]:
    """
    Reviewer Node: Evaluate the quality of gathered research.
    
    This node uses an LLM to assess whether the collected research
    adequately answers the user's query. It produces a score and
    decides whether to refine (loop back) or proceed.
    
    Args:
        state: Current graph state with gathered_context
        
    Returns:
        Updated state with latest_critique and incremented revision_count
    """
    user_query = state["user_query"]
    gathered_context = state.get("gathered_context", [])
    revision_count = state.get("revision_count", 0)
    
    # Format gathered research for evaluation
    research_summary = []
    for result in gathered_context:
        research_summary.append(f"\n### Step {result.step_id}: {result.query}")
        research_summary.append("Findings:")
        for i, finding in enumerate(result.results[:3], 1):  # Limit to top 3
            research_summary.append(f"  {i}. {finding[:500]}...")  # Truncate long content
        if result.sources:
            research_summary.append(f"Sources: {', '.join(result.sources[:3])}")
    
    research_text = "\n".join(research_summary)
    
    llm = get_llm()
    
    evaluation_prompt = f"""Original Query: {user_query}

Gathered Research:
{research_text}

Current Revision Count: {revision_count}/3

Please evaluate whether this research adequately answers the original query."""
    
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=evaluation_prompt)
    ]
    
    response = llm.invoke(messages)
    critique = parse_critique_response(response.content)
    
    # Increment revision count only if we need to refine
    new_revision_count = revision_count
    if critique.should_refine:
        new_revision_count = revision_count + 1
    
    # Convert response to AIMessage for proper message handling
    ai_message = AIMessage(content=response.content)
    
    return {
        "latest_critique": critique,
        "revision_count": new_revision_count,
        "messages": [ai_message],
    }
