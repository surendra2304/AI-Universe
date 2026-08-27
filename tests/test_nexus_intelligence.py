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
