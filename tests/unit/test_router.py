"""Unit tests for the Task Router and agent selection engine."""

import pytest
from app.agents.router import router


def test_router_domain_detection():
    # Debugging query
    agent = router.detect_domain_specialist("How do I fix this deadlock and trace the error traceback?")
    assert agent == "debugger"

    # Security query
    agent = router.detect_domain_specialist("Is there a potential prompt injection or secret leak vulnerability?")
    assert agent == "security_analyst"

    # Coding query
    agent = router.detect_domain_specialist("Implement a Python function with type annotations for rate limiting.")
    assert agent == "coder"

    # Data query
    agent = router.detect_domain_specialist("Analyze this SQL dataset and compute statistical distributions.")
    assert agent == "data_analyst"

    # General inquiry
    agent = router.detect_domain_specialist("Explain how photosynthesis works in plants.")
    assert agent == "researcher"


def test_router_fast_mode_routing():
    decision = router.route_task("Debug this segmentation fault crash.", requested_mode="fast")
    assert decision.mode == "fast"
    assert len(decision.selected_agent_ids) == 1
    assert decision.selected_agent_ids[0] == "debugger"


def test_router_review_mode_routing():
    decision = router.route_task("Implement a new user registration route in FastAPI.", requested_mode="review")
    assert decision.mode == "review"
    assert len(decision.selected_agent_ids) == 2
    assert "coder" in decision.selected_agent_ids
    assert "critic" in decision.selected_agent_ids


def test_router_debate_mode_routing():
    decision = router.route_task(
        "Compare the architecture trade-offs between monolithic and microservices designs for scale.",
        requested_mode="auto",
        max_agents=5
    )
    assert decision.mode == "debate"
    assert len(decision.selected_agent_ids) == 5
    assert "critic" in decision.selected_agent_ids
    assert "architect" in decision.selected_agent_ids


def test_router_explicit_mode_override():
    decision = router.route_task("Simple greeting", requested_mode="debate", max_agents=3)
    assert decision.mode == "debate"
    assert len(decision.selected_agent_ids) == 3
