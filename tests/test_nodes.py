"""Tests for individual node implementations."""

import pytest
from unittest.mock import patch, MagicMock

from src.research_assistant.state import (
    PlanStep,
    ResearchResult,
    CritiqueResult,
    create_initial_state,
)
from src.research_assistant.nodes.planner import planner_node, parse_plan_response
from src.research_assistant.nodes.researcher import researcher_node
from src.research_assistant.nodes.reviewer import reviewer_node, parse_critique_response
from src.research_assistant.nodes.writer import writer_node


class TestPlannerNode:
    """Tests for the Planner node."""
    
    def test_parse_plan_response_basic(self):
        """Test parsing a basic plan response."""
        response = """STEP 1: Research the basics of quantum computing
SEARCH: quantum computing fundamentals explained

STEP 2: Find recent breakthroughs
SEARCH: quantum computing breakthroughs 2024

STEP 3: Explore practical applications
SEARCH: quantum computing real world applications"""
        
        steps = parse_plan_response(response)
        
        assert len(steps) == 3
        assert steps[0].step_id == 1
        assert steps[0].task == "Research the basics of quantum computing"
        assert steps[0].search_query == "quantum computing fundamentals explained"
        assert steps[0].status == "pending"
    
    def test_parse_plan_response_empty(self):
        """Test parsing empty response returns empty list."""
        steps = parse_plan_response("")
        assert steps == []
    
    @patch('research_assistant.nodes.planner.get_llm')
    def test_planner_node_creates_plan(self, mock_get_llm):
        """Test planner node creates a plan from query."""
        # Mock LLM response
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """STEP 1: Research AI basics
SEARCH: artificial intelligence introduction"""
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = create_initial_state("What is AI?")
        result = planner_node(state)
        
        assert "current_plan" in result
        assert len(result["current_plan"]) >= 1
        assert result["current_step_idx"] == 0


class TestResearcherNode:
    """Tests for the Researcher node."""
    
    @patch('research_assistant.nodes.researcher.get_tavily_tool')
    def test_researcher_node_executes_search(self, mock_get_tavily):
        """Test researcher node executes search."""
        # Mock Tavily response
        mock_tavily = MagicMock()
        mock_tavily.invoke.return_value = [
            {"content": "AI is artificial intelligence", "url": "https://example.com"}
        ]
        mock_get_tavily.return_value = mock_tavily
        
        state = create_initial_state("What is AI?")
        state["current_plan"] = [
            PlanStep(step_id=1, task="Research AI", search_query="AI basics")
        ]
        state["current_step_idx"] = 0
        
        result = researcher_node(state)
        
        assert "gathered_context" in result
        assert len(result["gathered_context"]) == 1
        assert result["current_step_idx"] == 1
    
    def test_researcher_node_handles_empty_plan(self):
        """Test researcher handles empty plan gracefully."""
        state = create_initial_state("What is AI?")
        result = researcher_node(state)
        
        assert result["gathered_context"] == []


class TestReviewerNode:
    """Tests for the Reviewer node."""
    
    def test_parse_critique_response_high_score(self):
        """Test parsing high score critique."""
        response = """SCORE: 0.9
FEEDBACK: Excellent research with comprehensive coverage
SUGGESTIONS: None
SHOULD_REFINE: NO"""
        
        critique = parse_critique_response(response)
        
        assert critique.score == 0.9
        assert critique.should_refine is False
        assert critique.suggestions == []
    
    def test_parse_critique_response_low_score(self):
        """Test parsing low score critique that needs refinement."""
        response = """SCORE: 0.6
FEEDBACK: Research is incomplete
SUGGESTIONS: Add more sources, Include recent data
SHOULD_REFINE: YES"""
        
        critique = parse_critique_response(response)
        
        assert critique.score == 0.6
        assert critique.should_refine is True
        assert len(critique.suggestions) == 2
    
    def test_parse_critique_percentage_format(self):
        """Test parsing percentage format score."""
        response = """SCORE: 85%
FEEDBACK: Good coverage
SUGGESTIONS: None
SHOULD_REFINE: NO"""
        
        critique = parse_critique_response(response)
        assert critique.score == 0.85
    
    @patch('research_assistant.nodes.reviewer.get_llm')
    def test_reviewer_node_increments_revision_count(self, mock_get_llm):
        """Test reviewer increments revision count when refinement needed."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """SCORE: 0.5
FEEDBACK: Needs more work
SUGGESTIONS: Add details
SHOULD_REFINE: YES"""
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = create_initial_state("Test query")
        state["gathered_context"] = [
            ResearchResult(step_id=1, query="test", results=["result"])
        ]
        state["revision_count"] = 1
        
        result = reviewer_node(state)
        
        assert result["revision_count"] == 2
        assert result["latest_critique"].should_refine is True


class TestWriterNode:
    """Tests for the Writer node."""
    
    @patch('research_assistant.nodes.writer.get_llm')
    def test_writer_node_generates_response(self, mock_get_llm):
        """Test writer node generates final response."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "# Final Answer\n\nHere is the comprehensive response..."
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = create_initial_state("What is AI?")
        state["gathered_context"] = [
            ResearchResult(
                step_id=1,
                query="AI basics",
                results=["AI is artificial intelligence"],
                sources=["https://example.com"]
            )
        ]
        
        result = writer_node(state)
        
        assert "final_response" in result
        assert result["final_response"] is not None
    
    @patch('research_assistant.nodes.writer.get_llm')
    def test_writer_node_incorporates_human_feedback(self, mock_get_llm):
        """Test writer incorporates human feedback."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response with feedback incorporated"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = create_initial_state("What is AI?")
        state["gathered_context"] = []
        state["human_feedback"] = "Focus on practical applications"
        
        result = writer_node(state)
        
        # Verify LLM was called with feedback in prompt
        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        prompt_content = messages[1].content
        assert "Focus on practical applications" in prompt_content
