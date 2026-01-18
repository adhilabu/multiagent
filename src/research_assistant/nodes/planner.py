"""Planner Node - Breaks user query into actionable sub-tasks."""

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.research_assistant.state import ResearchState, PlanStep


# System prompt for the planner
PLANNER_SYSTEM_PROMPT = """You are a research planning expert. Your task is to break down a user's research query into clear, actionable sub-tasks.

For each sub-task, provide:
1. A clear description of what needs to be researched
2. A specific search query optimized for web search

Output your plan as a numbered list in this exact format:
STEP 1: [Description]
SEARCH: [Search query]

STEP 2: [Description]  
SEARCH: [Search query]

Continue for 3-5 steps depending on complexity. Be specific and focused.
Each step should build on previous steps to comprehensively answer the query."""


def get_llm() -> ChatOpenAI:
    """Initialize the LLM for planning."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
    )


def parse_plan_response(response: str) -> list[PlanStep]:
    """Parse the LLM response into structured PlanStep objects."""
    steps = []
    lines = response.strip().split("\n")
    
    current_step_id = 0
    current_task = ""
    current_query = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.upper().startswith("STEP"):
            # Save previous step if exists
            if current_task and current_query:
                steps.append(PlanStep(
                    step_id=current_step_id,
                    task=current_task,
                    search_query=current_query,
                    status="pending"
                ))
            
            # Start new step
            current_step_id += 1
            # Extract task description after "STEP N:"
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_task = parts[1].strip()
            current_query = ""
            
        elif line.upper().startswith("SEARCH:"):
            current_query = line.split(":", 1)[1].strip() if ":" in line else ""
    
    # Don't forget the last step
    if current_task and current_query:
        steps.append(PlanStep(
            step_id=current_step_id,
            task=current_task,
            search_query=current_query,
            status="pending"
        ))
    
    return steps


def planner_node(state: ResearchState) -> dict[str, Any]:
    """
    Planner Node: Break user query into actionable sub-tasks.
    
    This node analyzes the user's query and creates a structured
    research plan with 3-5 steps, each containing a specific
    search query for the Researcher node.
    
    Args:
        state: Current graph state with user_query
        
    Returns:
        Updated state with current_plan populated
    """
    user_query = state["user_query"]
    
    # Check if we're refining an existing plan (due to critique)
    existing_plan = state.get("current_plan", [])
    critique = state.get("latest_critique")
    
    llm = get_llm()
    
    if existing_plan and critique and critique.should_refine:
        # Refine the plan based on critique feedback
        refine_prompt = f"""The previous research plan didn't fully answer the query.

Original Query: {user_query}

Previous Plan:
{chr(10).join(f"Step {s.step_id}: {s.task}" for s in existing_plan)}

Critique Feedback: {critique.feedback}
Suggestions: {', '.join(critique.suggestions)}

Please create an IMPROVED research plan that addresses the gaps identified.
Focus on: {', '.join(critique.suggestions[:3]) if critique.suggestions else 'being more specific and comprehensive'}"""
        
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=refine_prompt)
        ]
    else:
        # Create initial plan
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"Research Query: {user_query}")
        ]
    
    response = llm.invoke(messages)
    plan_steps = parse_plan_response(response.content)
    
    # Ensure we have at least one step
    if not plan_steps:
        plan_steps = [PlanStep(
            step_id=1,
            task=f"Research: {user_query}",
            search_query=user_query,
            status="pending"
        )]
    
    # Convert response to AIMessage for proper message handling
    ai_message = AIMessage(content=response.content)
    
    return {
        "current_plan": plan_steps,
        "current_step_idx": 0,
        "messages": [ai_message],
    }
