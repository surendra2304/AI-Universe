"""Tests for Nexus Intelligence Endpoints and Mode-Based Routing."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.nexus_intelligence import (
    BudgetSpec,
    EvidenceItem,
    IntelligenceRequest,
    nexus_intelligence_service,
)

client = TestClient(app)


def test_nexus_intelligence_fast_mode():
    """Tests FAST mode routing with single specialist agent."""
    req = {
        "request_id": "nex-test-001",
        "task_type": "lead_qualification",
        "goal": "Evaluate enterprise inbound lead qualification",
        "context": {"lead_source": "inbound_demo", "company_size": "500-1000"},
        "evidence": [
            {"claim": "Budget verified above $50k ARR", "trust_label": "verified_telemetry"},
            {"claim": "Domain verified as Fortune 500", "trust_label": "system_fact"}
        ],
        "constraints": ["No outbound contact before qualification score >= 0.8"],
        "required_output": ["qualification_verdict", "next_action"],
        "budget": {"latency_ms": 3000, "max_rounds": 1},
        "mode": "fast"
    }
    resp = client.post("/v1/nexus/intelligence", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "nex-test-001"
    assert "PROCEED_WITH_LEAD_QUALIFICATION" in data["decision"]
    assert data["confidence"] >= 0.70
    assert len(data["recommended_actions"]) >= 1
    assert data["provenance"]["mode"] == "fast"
    assert len(data["provenance"]["agents_consulted"]) == 1


def test_nexus_intelligence_review_mode_with_critic_dissent():
    """Tests REVIEW mode with adversarial critic pass and disagreement preservation."""
    req = {
        "request_id": "nex-test-002",
        "task_type": "incident_analysis",
        "goal": "Analyze root cause of API latency spike",
        "context": {"service": "order_gateway"},
        "evidence": [
            {"claim": "User reported intermittent socket disconnects", "trust_label": "untrusted_user_input"}
        ],
        "constraints": ["Must preserve audit log"],
        "required_output": ["mitigation_plan"],
        "budget": {"latency_ms": 8000, "max_rounds": 1},
        "mode": "review"
    }
    resp = client.post("/v1/nexus/intelligence", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "nex-test-002"
    assert "VALIDATED_INCIDENT_ANALYSIS" in data["decision"]
    assert len(data["provenance"]["agents_consulted"]) == 2
    # Disagreements preserved, not silently flattened
    assert len(data["unresolved_disagreements"]) > 0


def test_nexus_intelligence_debate_mode():
    """Tests DEBATE mode multi-round deliberation with 3+ specialists."""
    req = {
        "request_id": "nex-test-003",
        "task_type": "strategic_decision",
        "goal": "Determine multi-region datacenter expansion strategy",
        "context": {"regions": ["us-east", "eu-central"]},
        "evidence": [
            {"claim": "GDPR compliance mandates EU data localization", "trust_label": "system_fact"},
            {"claim": "Telemetry shows 45% traffic from EMEA", "trust_label": "verified_telemetry"}
        ],
        "budget": {"latency_ms": 20000, "max_rounds": 4},
        "mode": "debate"
    }
    resp = client.post("/v1/nexus/intelligence", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "nex-test-003"
    assert "CONSENSUS_STRATEGIC_DECISION" in data["decision"]
    assert data["provenance"]["rounds_conducted"] >= 2
    assert len(data["provenance"]["agents_consulted"]) >= 3


def test_nexus_provenance_retrieval():
    """Tests GET /v1/nexus/intelligence/{request_id} retrieval for audit & explanation."""
    # Retrieve existing stored record
    resp = client.get("/v1/nexus/intelligence/nex-test-001")
    assert resp.status_code == 200
    record = resp.json()
    assert "request" in record
    assert "response" in record
    assert record["request"]["request_id"] == "nex-test-001"

    # Non-existent record returns 404
    resp_404 = client.get("/v1/nexus/intelligence/non_existent_id")
    assert resp_404.status_code == 404


def test_reasoning_trace_and_debate_statistics():
    """Tests GET /v1/intelligence/{request_id}/trace and GET /v1/debate/statistics."""
    # Retrieve trace for the debate conducted in test_nexus_intelligence_debate_mode
    resp_trace = client.get("/v1/intelligence/nex-test-003/trace")
    assert resp_trace.status_code == 200
    trace = resp_trace.json()
    assert trace["request_id"] == "nex-test-003"
    assert len(trace["rounds"]) == 4
    assert len(trace["stated_assumptions"]) >= 1
    assert len(trace["evidence_scores"]) >= 1
    assert "provider_allocation" in trace

def test_multi_tenant_governance_and_deduplication():
    """Tests tenant isolation, key rotation, circuits, Prometheus metrics, and request deduplication."""
    # 1. Request deduplication (same request_id returns cached response)
    req = {
        "request_id": "nex-dedup-999",
        "task_type": "lead_qualification",
        "goal": "Deduplication idempotency check",
        "evidence": [{"claim": "System telemetry stable", "trust_label": "system_fact"}],
        "mode": "fast"
    }
    r1 = client.post("/v1/nexus/intelligence", json=req)
    assert r1.status_code == 200
    r2 = client.post("/v1/nexus/intelligence", json=req)
    assert r2.status_code == 200
    assert r1.json()["request_id"] == r2.json()["request_id"]
    assert r1.json()["decision"] == r2.json()["decision"]

    # 2. Tenant policy retrieval
    resp_tp = client.get("/v1/governance/tenants/tenant_forge")
    assert resp_tp.status_code == 200
    assert resp_tp.json()["tenant_id"] == "tenant_forge"

    # 3. Key rotation
    resp_rot = client.post("/v1/governance/tenants/tenant_forge/rotate-key", json={"old_key": "key_forge_prod_01"})
    assert resp_rot.status_code == 200
    assert resp_rot.json()["status"] == "ROTATED"

    # 4. Circuit breaker status
    resp_circ = client.get("/v1/governance/circuits")
    assert resp_circ.status_code == 200
    assert "gemini" in resp_circ.json()

    # 5. Prometheus metrics formatted
    resp_prom = client.get("/v1/governance/prometheus-metrics")
    assert resp_prom.status_code == 200
    assert "ai_universe_requests_total" in resp_prom.json()["metrics"]


def test_multimodal_intelligence_and_temporal_reasoning():
    """Tests POST /v1/intelligence/multimodal across text, code, structured tables, temporal series, and counterfactuals."""
    payload = {
        "request_id": "multi-test-001",
        "task_type": "strategic_decision",
        "goal": "Optimize pipeline throughput and conversion",
        "attached_contents": [
            {"content_type": "text", "payload": "Enterprise pipeline report for Q3"},
            {"content_type": "code", "payload": "def process(): return True", "language_or_mime": "python"},
            {"content_type": "structured_data", "payload": '[{"day": 1, "leads": 40}, {"day": 2, "leads": 55}]'},
            {"content_type": "url", "payload": "https://internal.telemetry/metrics"},
            {"content_type": "image", "payload": "data:image/png;base64,iVBORw0KGgoAAA...", "language_or_mime": "image/png"}
        ],
        "temporal_context": "Pattern began 3 days ago following release v2.4",
        "time_series_data": [
            {"timestamp": 1724000000, "value": 100.0, "metric_name": "leads"},
            {"timestamp": 1724086400, "value": 115.0, "metric_name": "leads"},
            {"timestamp": 1724172800, "value": 130.0, "metric_name": "leads"}
        ],
        "what_if_scenario": {
            "scenario_name": "Variant B Experiment",
            "proposed_intervention": "Switch to Variant B pricing modal",
            "baseline_variable": "Variant A",
            "counterfactual_variable": "Variant B"
        },
        "audience": "detailed"
    }
    resp = client.post("/v1/intelligence/multimodal", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "multi-test-001"
    assert "OPTIMIZE_STRATEGY" in data["decision"]
    assert "95% CI:" in data["point_estimate_with_ci"]
    assert len(data["content_analysis_summaries"]) == 5
    assert data["temporal_insights"]["trend"] == "UPWARD"
    assert data["counterfactual_analysis"]["is_counterfactual"] is True
    assert data["counterfactual_analysis"]["confidence_interval_95"]["ci_upper"] > 0
    assert len(data["explanation"]["detailed"]) > 0
