"""Writer Node - Synthesizes final comprehensive response."""

import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.research_assistant.state import ResearchState


WRITER_SYSTEM_PROMPT = """You are an expert research synthesizer. Your task is to create a comprehensive, well-structured answer based on gathered research.

Guidelines:
1. STRUCTURE: Use clear headings and organize information logically
2. CITATIONS: Reference sources where applicable using [Source N] format
3. COMPLETENESS: Address all aspects of the original query
4. CLARITY: Write in clear, accessible language
5. ACCURACY: Only include information supported by the research

If human feedback was provided, incorporate it into your response.

Format your response with:
- A brief executive summary
- Main body with key findings organized by topic
- A conclusion summarizing the answer
- List of sources at the end"""


def get_llm() -> ChatOpenAI:
    """Initialize the LLM for writing."""
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
    )


def writer_node(state: ResearchState) -> dict[str, Any]:
    """
    Writer Node: Synthesize final comprehensive response.
    
    This node combines all gathered research and any human feedback
    to produce a well-structured, comprehensive answer to the
    user's original query.
    
    Args:
        state: Current graph state with gathered_context and optional human_feedback
        
    Returns:
        Updated state with final_response
    """
    user_query = state["user_query"]
    gathered_context = state.get("gathered_context", [])
    human_feedback = state.get("human_feedback")
    
    # Format all research for synthesis
    all_sources = []
    research_sections = []
    
    for result in gathered_context:
        section = f"\n## Research for: {result.query}\n"
        for i, finding in enumerate(result.results, 1):
            section += f"\n{i}. {finding}\n"
        research_sections.append(section)
        all_sources.extend(result.sources)
    
    research_text = "\n".join(research_sections)
    
    # Deduplicate sources
    unique_sources = list(dict.fromkeys(all_sources))
    sources_text = "\n".join(f"[{i+1}] {src}" for i, src in enumerate(unique_sources))
    
    llm = get_llm()
    
    write_prompt = f"""Original Query: {user_query}

Gathered Research:
{research_text}

Available Sources:
{sources_text}"""
    
    if human_feedback:
        write_prompt += f"""

Human Feedback to Incorporate:
{human_feedback}"""
    
    write_prompt += """

Please synthesize a comprehensive response that fully addresses the original query."""
    
    messages = [
        SystemMessage(content=WRITER_SYSTEM_PROMPT),
        HumanMessage(content=write_prompt)
    ]
    
    response = llm.invoke(messages)
    
    # Convert response to AIMessage for proper message handling
    ai_message = AIMessage(content=response.content)
    
    return {
        "final_response": response.content,
        "messages": [ai_message],
    }
