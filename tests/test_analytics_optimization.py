"""Tests for Usage Analytics, Provider Intelligence, Self-Optimization, and Admin Dashboards."""

import pytest
from fastapi.testclient import TestClient

from app.analytics.outcomes import OutcomeReportRequest, consumer_outcome_tracker
from app.analytics.predictive import predictive_provider_manager
from app.analytics.provider_intel import provider_intel
from app.analytics.usage_analytics import usage_analytics
from app.main import app
from app.routing.self_optimizer import self_optimizing_router
from app.services.quality_assurance import quality_assurance_service

client = TestClient(app)


def test_usage_analytics_engine():
    """Tests request logging, cost attribution, and consumer breakdowns."""
    usage_analytics.log_request(
        consumer="forge",
        service="generate-code",
        provider="groq",
        tokens_in=300,
        tokens_out=600,
        latency_ms=28.0,
        success=True,
        confidence=0.95
    )
    overview = usage_analytics.get_overview()
    assert overview["total_calls"] >= 4
    assert overview["total_tokens"] > 0
    assert overview["total_cost_usd"] > 0

    c_breakdown = usage_analytics.get_consumer_breakdown("forge")
    assert c_breakdown["calls"] >= 2
    assert c_breakdown["success_rate_pct"] == 100.0


def test_provider_intelligence_and_failure_analysis():
    """Tests provider performance matrix and routing recommendations."""
    matrix = provider_intel.get_performance_matrix()
    assert "groq" in matrix["provider_service_matrix"]
    assert "gemini" in matrix["provider_service_matrix"]
    assert len(matrix["routing_recommendations"]) >= 2


def test_consumer_outcome_tracking_and_self_optimizer():
    """Tests outcome reporting and dynamic weight adaptation."""
    req = OutcomeReportRequest(
        consumer="forge",
        request_id="req-test-99",
        outcome="success",
        detail="verification_passed",
        provider_used="gemini",
        service="code_generation"
    )
    res = consumer_outcome_tracker.record_outcome(req)
    assert res["status"] == "RECORDED"

    # Adapt weights
    self_optimizing_router.adapt_weights_from_outcomes()
    status_data = self_optimizing_router.get_routing_status()
    assert "active_weights" in status_data
    assert "code_generation" in status_data["active_weights"]


def test_quality_assurance_ast_and_calibration():
    """Tests AST Python parser and quality reports."""
    # Valid Python code
    valid_res = quality_assurance_service.evaluate_code_syntax("def hello():\n    return 'world'")
    assert valid_res["is_valid"] is True
    assert valid_res["error"] is None

    # Invalid Python code
    invalid_res = quality_assurance_service.evaluate_code_syntax("def hello(:\n    return 'world'")
    assert invalid_res["is_valid"] is False
    assert "SyntaxError" in invalid_res["error"]

    report = quality_assurance_service.get_quality_report()
    assert report["overall_output_quality_score"] > 90.0


def test_analytics_and_admin_api_endpoints():
    """Tests GET /v1/analytics/overview, /v1/admin/dashboard, /v1/admin/alerts."""
    # Analytics overview
    resp_ov = client.get("/v1/analytics/overview")
    assert resp_ov.status_code == 200
    assert "total_calls" in resp_ov.json()

    # Admin dashboard
    resp_dash = client.get("/v1/admin/dashboard")
    assert resp_dash.status_code == 200
    data = resp_dash.json()
    assert "usage_overview" in data
    assert "provider_comparison" in data
    assert "predictive_forecast" in data

    # Outcome reporting endpoint
    payload = {
        "consumer": "forge",
        "request_id": "test-endpoint-outcome",
        "outcome": "success",
        "detail": "verification_passed",
        "measured_metrics": {"build_time_s": 2.1},
        "task_type": "code_generation",
        "provider_used": "gemini"
    }
    resp_out = client.post("/v1/analytics/outcome", json=payload)
    assert resp_out.status_code == 200
    assert resp_out.json()["status"] == "RECORDED"

    # Calibration endpoint
    resp_cal = client.get("/v1/analytics/calibration")
    assert resp_cal.status_code == 200
    assert "calibration_curve" in resp_cal.json()

    # Cross consumer insights endpoint
    resp_ins = client.get("/v1/analytics/insights")
    assert resp_ins.status_code == 200
    assert "cross_consumer_patterns" in resp_ins.json()

    # Strategy bank endpoint
    resp_sb = client.get("/v1/analytics/strategy-bank?task_type=lead_qualification")
    assert resp_sb.status_code == 200
    assert len(resp_sb.json()) >= 1

    # Optimization status endpoint
    resp_opt = client.get("/v1/admin/optimization/status")
    assert resp_opt.status_code == 200
    assert "active_weights" in resp_opt.json()


def test_cost_aware_routing_and_token_optimization():
    """Tests CostAwareRouter, TokenOptimizationEngine, and ProviderCostTracker."""
    from app.token_optimizer import token_optimizer
    from app.routing.cost_router import cost_aware_router
    from app.analytics.cost_tracking import provider_cost_tracker

    # 1. Cost-aware routing
    route_dec = cost_aware_router.route_request("nexus", "lead_qualification", estimated_tokens=1200)
    assert route_dec.selected_provider in ("groq", "gemini", "nvidia", "mistral", "openrouter")
    assert route_dec.cost_efficiency_score > 0

    # 2. Token compression
    comp_res = token_optimizer.compress_context(
        context={"goal": "Evaluate ARR lead", "meta": "Additional details that can be compressed"},
        evidence_list=[
            {"claim": "Verified telemetry", "trust_label": "verified_telemetry"},
            {"claim": "User unverified text", "trust_label": "untrusted_user_input"}
        ],
        max_evidence=2
    )
    assert comp_res.compression_ratio_pct >= 40.0
    assert len(comp_res.selected_evidence) <= 2

    # 3. Semantic caching
    token_optimizer.store_cached_response("trading", "BTC volatile market query", {"advice": "DECREASE_LEVERAGE"})
    hit = token_optimizer.get_cached_response("trading", "BTC volatile market query")
    assert hit is not None
    assert hit["advice"] == "DECREASE_LEVERAGE"

    # 4. Admin costs & budget dashboard
    resp_cost = client.get("/v1/admin/costs")
    assert resp_cost.status_code == 200
    data = resp_cost.json()
    assert "cost_per_successful_outcome_usd" in data
    assert "consumer_budgets" in data

    resp_bud = client.get("/v1/admin/budgets")
    assert resp_bud.status_code == 200
    assert "trading_bot" in resp_bud.json()
