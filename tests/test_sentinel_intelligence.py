"""Unit & Integration Tests for Sentinel Security Intelligence Endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sentinel_vulnerability_assessment():
    """Tests POST /v1/sentinel/analyze for vulnerability_assessment."""
    req = {
        "request_id": "sent-test-001",
        "analysis_type": "vulnerability_assessment",
        "target_context": {
            "asset_type": "api_gateway",
            "technologies_detected": ["FastAPI", "Python", "Nginx"],
            "exposure_level": "public_internet"
        },
        "findings": [
            {
                "finding_id": "F-01",
                "severity": "HIGH",
                "title": "Missing Security Headers",
                "description": "Strict-Transport-Security header is not set on TLS listener.",
                "evidence_refs": ["header_audit_log_line_45"],
                "cvss_score": 7.5
            },
            {
                "finding_id": "F-02",
                "severity": "LOW",
                "title": "Server Banner Disclosure",
                "description": "Server header exposes Nginx version.",
                "evidence_refs": ["response_header_server"],
                "cvss_score": 2.5
            }
        ],
        "threat_intel": {
            "cve_matches": ["CVE-2026-GATE-01"],
            "exploit_availability": "poc",
            "threat_actor_activity": "low"
        },
        "constraints": {
            "scan_mode": "standard",
            "time_budget": 10
        }
    }
    resp = client.post("/v1/sentinel/analyze", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "sent-test-001"
    assert "HIGH" in data["analysis"]["risk_assessment"]["risk_tier"]
    assert len(data["analysis"]["prioritized_remediation"]) == 2
    assert data["analysis"]["confidence"] >= 0.85
    assert len(data["safety_notes"]) >= 1


def test_sentinel_attack_path_reasoning_debate():
    """Tests POST /v1/sentinel/analyze for attack_path_reasoning with adversarial debate."""
    req = {
        "request_id": "sent-test-002",
        "analysis_type": "attack_path_reasoning",
        "target_context": {
            "asset_type": "web_app",
            "technologies_detected": ["Node.js", "PostgreSQL"],
            "exposure_level": "public_internet"
        },
        "findings": [
            {
                "finding_id": "F-10",
                "severity": "CRITICAL",
                "title": "Unauthenticated Parameter Exposure",
                "description": "Endpoint permits parameter tampering without validation.",
                "cvss_score": 9.2
            }
        ],
        "threat_intel": {
            "cve_matches": ["CVE-2026-AUTH-09"],
            "exploit_availability": "in_the_wild",
            "threat_actor_activity": "active_campaign"
        }
    }
    resp = client.post("/v1/sentinel/analyze", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "sent-test-002"
    assert data["analysis"]["attack_paths"] is not None
    assert len(data["analysis"]["attack_paths"]) >= 1
    assert data["analysis"]["attack_paths"][0]["overall_probability"] > 0
    # Dissent from adversarial debate pass preserved
    assert len(data["analysis"]["dissent"]) >= 1


def test_sentinel_provenance_retrieval():
    """Tests GET /v1/sentinel/analyze/{request_id} retrieval for audit & explanation."""
    resp = client.get("/v1/sentinel/analyze/sent-test-001")
    assert resp.status_code == 200
    record = resp.json()
    assert "request" in record
    assert "response" in record
    assert record["request"]["request_id"] == "sent-test-001"

    # Non-existent ID returns 404
    resp_404 = client.get("/v1/sentinel/analyze/non_existent_sentinel_id")
    assert resp_404.status_code == 404


def test_threat_context_and_remediation_reasoning():
    """Tests ThreatContextEngine and RemediationReasoningEngine components."""
    from app.intelligence.threat_context import threat_context_engine
    from app.intelligence.remediation import remediation_reasoning_engine, SecurityOutcomeRecord

    # 1. Threat context enrichment
    enriched = threat_context_engine.enrich_context(
        technologies=["FastAPI", "Python"],
        exposure_level="public_internet",
        cve_matches=["CVE-2026-AUTH-01"],
        industry="fintech"
    )
    assert len(enriched.active_threat_campaigns) >= 1
    assert "CVE-2026-AUTH-01" in enriched.cve_exploitation_trends
    assert enriched.threat_elevation_factor >= 1.0

    # 2. Dependency-aware remediation planning
    plan = remediation_reasoning_engine.plan_remediations(
        findings=[
            {"finding_id": "F-01", "title": "Missing Security Headers", "severity": "HIGH"},
            {"finding_id": "F-02", "title": "Server Banner Disclosure", "severity": "LOW"}
        ],
        exposure_level="public_internet"
    )
    assert len(plan) == 2
    assert plan[0].quick_win is True

    # 3. Security outcome tracking
    remediation_reasoning_engine.record_security_outcome(
        SecurityOutcomeRecord(
            request_id="sent-test-001",
            finding_id="F-01",
            remediation_applied="Set Strict-Transport-Security in Nginx",
            verified_resolved=True,
            rescan_timestamp=1724880500.0
        )
    )
    metrics = remediation_reasoning_engine.get_security_learning_metrics()
    assert metrics["verified_resolution_rate_pct"] > 80.0
