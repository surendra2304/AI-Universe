"""Unit tests for the Task Router, budget/latency degradation, and policy engine."""

from app.agents.router import router
from app.core.policies import ProviderSwitchingPolicy, SwitchReason


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
    assert decision.degraded is False
    assert decision.telemetry["final_mode"] == "fast"


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
    assert decision.degraded is False


def test_router_budget_degradation_guardrails():
    # A complex question that would normally trigger debate, but budget is very tight ($0.001)
    decision = router.route_task(
        "Compare the architecture trade-offs between monolithic and microservices designs for scale.",
        requested_mode="debate",
        max_budget=0.002
    )
    assert decision.mode == "fast"
    assert decision.degraded is True
    assert "forced degradation from debate to fast mode" in decision.reason
    assert decision.telemetry["degraded"] is True

    # Moderate budget constraint ($0.015) degrades debate -> review
    decision_review = router.route_task(
        "Compare the architecture trade-offs between monolithic and microservices designs for scale.",
        requested_mode="debate",
        max_budget=0.015
    )
    assert decision_review.mode == "review"
    assert decision_review.degraded is True
    assert "forced degradation from debate to review mode" in decision_review.reason


def test_router_latency_degradation_guardrails():
    # Strict latency limit (< 3s) forces degradation to fast
    decision = router.route_task(
        "Evaluate the security posture and trade-offs of microservices authentication.",
        requested_mode="debate",
        max_latency=2.5
    )
    assert decision.mode == "fast"
    assert decision.degraded is True
    assert len(decision.selected_agent_ids) == 1

    # Moderate latency limit (8s) degrades debate -> review
    decision_review = router.route_task(
        "Evaluate the security posture and trade-offs of microservices authentication.",
        requested_mode="debate",
        max_latency=8.0
    )
    assert decision_review.mode == "review"
    assert decision_review.degraded is True
    assert len(decision_review.selected_agent_ids) == 2


def test_router_triviality_guardrail():
    # Trivial short greeting or phrase requesting debate should degrade to fast mode
    decision = router.route_task("hello there", requested_mode="debate")
    assert decision.mode == "fast"
    assert decision.degraded is True
    assert "Trivial query guardrail" in decision.reason


def test_provider_switching_policy():
    # Fallback matrix checks
    fallback = ProviderSwitchingPolicy.get_fallback_provider("gemini", SwitchReason.QUOTA, stage="round_1")
    assert fallback is not None
    assert fallback.fallback_provider == "openrouter"
    assert fallback.fallback_model == "nvidia/nemotron-3.5-lightning:free"

    groq_fallback = ProviderSwitchingPolicy.get_fallback_provider("groq", SwitchReason.LATENCY)
    assert groq_fallback is not None
    assert groq_fallback.fallback_provider == "nvidia"

    # Consequential stage restriction
    assert ProviderSwitchingPolicy.can_switch_in_stage("cross_review_critique", allow_mid_stage=False) is False
    assert ProviderSwitchingPolicy.can_switch_in_stage("consensus_synthesis", allow_mid_stage=False) is False
    assert ProviderSwitchingPolicy.can_switch_in_stage("round_1_analysis", allow_mid_stage=False) is True
    assert ProviderSwitchingPolicy.can_switch_in_stage("consensus_synthesis", allow_mid_stage=True) is True
