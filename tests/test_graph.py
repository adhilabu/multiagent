"""Tests for graph construction and routing logic."""

import pytest
from unittest.mock import patch, MagicMock

from src.research_assistant.state import (
    PlanStep,
    ResearchResult,
    CritiqueResult,
    create_initial_state,
)
from src.research_assistant.graph import (
    build_graph,
    route_after_review,
    should_continue_research,
    create_app_without_persistence,
    MAX_REVISIONS,
)


class TestRouteAfterReview:
    """Tests for the routing decision after review."""
    
    def test_route_to_writer_when_score_high(self):
        """Test routing to writer when critique score is high."""
        state = create_initial_state("test")
        state["latest_critique"] = CritiqueResult(
            score=0.9,
            feedback="Excellent",
            should_refine=False
        )
        state["revision_count"] = 0
        
        result = route_after_review(state)
        assert result == "writer"
    
    def test_route_to_researcher_when_score_low(self):
        """Test routing back to researcher when score is low."""
        state = create_initial_state("test")
        state["latest_critique"] = CritiqueResult(
            score=0.5,
            feedback="Needs improvement",
            should_refine=True
        )
        state["revision_count"] = 1
        
        result = route_after_review(state)
        assert result == "researcher"
    
    def test_route_to_force_end_when_max_revisions(self):
        """Test force ending when max revisions exceeded."""
        state = create_initial_state("test")
        state["latest_critique"] = CritiqueResult(
            score=0.3,
            feedback="Still bad",
            should_refine=True
        )
        state["revision_count"] = MAX_REVISIONS + 1  # Exceeds max
        
        result = route_after_review(state)
        assert result == "force_end"
    
    def test_route_to_writer_at_max_revisions(self):
        """Test routing to writer at exactly max revisions with good score."""
        state = create_initial_state("test")
        state["latest_critique"] = CritiqueResult(
            score=0.85,
            feedback="Good enough",
            should_refine=False
        )
        state["revision_count"] = MAX_REVISIONS
        
        result = route_after_review(state)
        assert result == "writer"


class TestShouldContinueResearch:
    """Tests for research continuation logic."""
    
    def test_continue_when_steps_remain(self):
        """Test continuing research when steps remain."""
        state = create_initial_state("test")
        state["current_plan"] = [
            PlanStep(step_id=1, task="Step 1"),
            PlanStep(step_id=2, task="Step 2"),
        ]
        state["current_step_idx"] = 0
        
        result = should_continue_research(state)
        assert result == "researcher"
    
    def test_go_to_reviewer_when_all_steps_done(self):
        """Test going to reviewer when all steps completed."""
        state = create_initial_state("test")
        state["current_plan"] = [
            PlanStep(step_id=1, task="Step 1"),
            PlanStep(step_id=2, task="Step 2"),
        ]
        state["current_step_idx"] = 2  # Past last step
        
        result = should_continue_research(state)
        assert result == "reviewer"
    
    def test_go_to_reviewer_on_empty_plan(self):
        """Test going to reviewer with empty plan."""
        state = create_initial_state("test")
        state["current_plan"] = []
        state["current_step_idx"] = 0
        
        result = should_continue_research(state)
        assert result == "reviewer"


class TestBuildGraph:
    """Tests for graph construction."""
    
    def test_build_graph_returns_state_graph(self):
        """Test that build_graph returns a valid StateGraph."""
        graph = build_graph()
        assert graph is not None
    
    def test_graph_has_all_nodes(self):
        """Test that graph contains all required nodes."""
        graph = build_graph()
        
        # Check nodes are registered
        assert "planner" in graph.nodes
        assert "researcher" in graph.nodes
        assert "reviewer" in graph.nodes
        assert "writer" in graph.nodes
    
    def test_create_app_without_persistence(self):
        """Test creating app without persistence for testing."""
        app = create_app_without_persistence(enable_hitl=False)
        assert app is not None


class TestGraphIntegration:
    """Integration tests for the complete graph flow."""
    
    @patch('research_assistant.nodes.planner.get_llm')
    @patch('research_assistant.nodes.researcher.get_tavily_tool')
    @patch('research_assistant.nodes.reviewer.get_llm')
    @patch('research_assistant.nodes.writer.get_llm')
    def test_full_graph_flow_success(
        self,
        mock_writer_llm,
        mock_reviewer_llm,
        mock_tavily,
        mock_planner_llm
    ):
        """Test complete flow with mocked dependencies."""
        # Mock planner
        planner_mock = MagicMock()
        planner_response = MagicMock()
        planner_response.content = """STEP 1: Research topic
SEARCH: test query"""
        planner_mock.invoke.return_value = planner_response
        mock_planner_llm.return_value = planner_mock
        
        # Mock tavily
        tavily_mock = MagicMock()
        tavily_mock.invoke.return_value = [
            {"content": "Test result", "url": "https://example.com"}
        ]
        mock_tavily.return_value = tavily_mock
        
        # Mock reviewer (high score, no refinement)
        reviewer_mock = MagicMock()
        reviewer_response = MagicMock()
        reviewer_response.content = """SCORE: 0.9
FEEDBACK: Good
SUGGESTIONS: None
SHOULD_REFINE: NO"""
        reviewer_mock.invoke.return_value = reviewer_response
        mock_reviewer_llm.return_value = reviewer_mock
        
        # Mock writer
        writer_mock = MagicMock()
        writer_response = MagicMock()
        writer_response.content = "Final comprehensive response"
        writer_mock.invoke.return_value = writer_response
        mock_writer_llm.return_value = writer_mock
        
        # Run the graph
        app = create_app_without_persistence(enable_hitl=False)
        initial_state = create_initial_state("Test research query")
        
        result = app.invoke(initial_state)
        
        assert result["final_response"] == "Final comprehensive response"
        assert len(result["gathered_context"]) > 0
    
    @patch('research_assistant.nodes.planner.get_llm')
    @patch('research_assistant.nodes.researcher.get_tavily_tool')
    @patch('research_assistant.nodes.reviewer.get_llm')
    def test_self_correction_loop(
        self,
        mock_reviewer_llm,
        mock_tavily,
        mock_planner_llm
    ):
        """Test that self-correction loop works with revision count."""
        # Mock planner
        planner_mock = MagicMock()
        planner_response = MagicMock()
        planner_response.content = """STEP 1: Research
SEARCH: query"""
        planner_mock.invoke.return_value = planner_response
        mock_planner_llm.return_value = planner_mock
        
        # Mock tavily
        tavily_mock = MagicMock()
        tavily_mock.invoke.return_value = []
        mock_tavily.return_value = tavily_mock
        
        # Mock reviewer - always returns low score to trigger loop
        reviewer_mock = MagicMock()
        reviewer_response = MagicMock()
        reviewer_response.content = """SCORE: 0.3
FEEDBACK: Bad
SUGGESTIONS: Improve
SHOULD_REFINE: YES"""
        reviewer_mock.invoke.return_value = reviewer_response
        mock_reviewer_llm.return_value = reviewer_mock
        
        # Run the graph
        app = create_app_without_persistence(enable_hitl=False)
        initial_state = create_initial_state("Test query")
        
        result = app.invoke(initial_state)
        
        # Should hit max revisions and force end
        assert result["revision_count"] > MAX_REVISIONS
        # Should not have final response since it was force ended
        assert result.get("final_response") is None
