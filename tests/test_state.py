"""Tests for state schema and Pydantic models."""

import pytest
from src.research_assistant.state import (
    PlanStep,
    ResearchResult,
    CritiqueResult,
    ResearchState,
    create_initial_state,
)


class TestPlanStep:
    """Tests for PlanStep model."""
    
    def test_create_plan_step(self):
        """Test creating a valid PlanStep."""
        step = PlanStep(
            step_id=1,
            task="Research quantum computing basics",
            search_query="quantum computing introduction 2024"
        )
        
        assert step.step_id == 1
        assert step.task == "Research quantum computing basics"
        assert step.search_query == "quantum computing introduction 2024"
        assert step.status == "pending"
    
    def test_plan_step_status_default(self):
        """Test default status is 'pending'."""
        step = PlanStep(step_id=1, task="Test task")
        assert step.status == "pending"
    
    def test_plan_step_update_status(self):
        """Test updating step status."""
        step = PlanStep(step_id=1, task="Test task")
        updated = step.model_copy(update={"status": "completed"})
        
        assert updated.status == "completed"
        assert step.status == "pending"  # Original unchanged


class TestResearchResult:
    """Tests for ResearchResult model."""
    
    def test_create_research_result(self):
        """Test creating a valid ResearchResult."""
        result = ResearchResult(
            step_id=1,
            query="test query",
            results=["Finding 1", "Finding 2"],
            sources=["https://example.com"],
            relevance_score=0.85
        )
        
        assert result.step_id == 1
        assert len(result.results) == 2
        assert result.relevance_score == 0.85
    
    def test_research_result_defaults(self):
        """Test default values."""
        result = ResearchResult(step_id=1, query="test")
        
        assert result.results == []
        assert result.sources == []
        assert result.relevance_score == 0.0


class TestCritiqueResult:
    """Tests for CritiqueResult model."""
    
    def test_create_critique_result(self):
        """Test creating a valid CritiqueResult."""
        critique = CritiqueResult(
            score=0.75,
            feedback="Results are partially relevant",
            suggestions=["Add more specific sources", "Focus on recent data"],
            should_refine=True
        )
        
        assert critique.score == 0.75
        assert critique.should_refine is True
        assert len(critique.suggestions) == 2
    
    def test_critique_defaults(self):
        """Test default values."""
        critique = CritiqueResult(score=0.9, feedback="Good")
        
        assert critique.suggestions == []
        assert critique.should_refine is False


class TestCreateInitialState:
    """Tests for create_initial_state function."""
    
    def test_create_initial_state(self):
        """Test creating initial state with a query."""
        state = create_initial_state("What is machine learning?")
        
        assert state["user_query"] == "What is machine learning?"
        assert state["messages"] == []
        assert state["current_plan"] == []
        assert state["current_step_idx"] == 0
        assert state["gathered_context"] == []
        assert state["latest_critique"] is None
        assert state["revision_count"] == 0
        assert state["human_approved"] is False
        assert state["human_feedback"] is None
        assert state["final_response"] is None
    
    def test_create_initial_state_empty_query(self):
        """Test creating initial state with empty query."""
        state = create_initial_state("")
        assert state["user_query"] == ""
