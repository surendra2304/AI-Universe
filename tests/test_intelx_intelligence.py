"""Unit & Integration Tests for IntelX Deep Research Intelligence Endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_intelx_research_planner_role():
    """Tests POST /v1/intelx/research for planner role."""
    req = {
        "request_id": "intelx-test-001",
        "role": "planner",
        "context": {
            "question": "What are the security and scalability implications of decentralized sequencer networks?",
            "subquestions": []
        }
    }
    resp = client.post("/v1/intelx/research", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "intelx-test-001"
    assert data["role"] == "planner"
    assert "execution_plan" in data["response"]
    assert len(data["response"]["subquestions_planned"]) >= 2
    assert data["confidence"] >= 0.90


def test_intelx_research_verifier_role_with_dissent():
    """Tests POST /v1/intelx/research for verifier role running Fact Checker + Critic debate."""
    req = {
        "request_id": "intelx-test-002",
        "role": "verifier",
        "context": {
            "question": "Verify TPS benchmarks across rollup frameworks"
        },
        "evidence_with_spans": [
            {
                "claim": "Rollup A achieves 10,000 TPS on testnet",
                "verbatim_span": "demonstrated sustained 10,000 TPS under artificial stress load",
                "document_source": "https://wire.news/benchmark-report",
                "credibility_score": 0.88
            },
            {
                "claim": "Rollup A achieves 10,000 TPS on testnet",
                "verbatim_span": "demonstrated sustained 10,000 TPS under artificial stress load",
                "document_source": "https://syndicated-mirror.com/benchmark-report",
                "credibility_score": 0.55
            }
        ]
    }
    resp = client.post("/v1/intelx/research", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "intelx-test-002"
    assert data["role"] == "verifier"
    assert "verification_matrix" in data["response"]
    # Syndication detected and flagged
    assert len(data["source_independence_flags"]) >= 1
    # Critic dissent recorded
    assert len(data["dissent"]) >= 1


def test_intelx_research_provenance_retrieval():
    """Tests GET /v1/intelx/research/{request_id} retrieval for audit & explanation."""
    resp = client.get("/v1/intelx/research/intelx-test-001")
    assert resp.status_code == 200
    record = resp.json()
    assert "request" in record
    assert "response" in record
    assert record["request"]["request_id"] == "intelx-test-001"

    # Non-existent ID returns 404
    resp_404 = client.get("/v1/intelx/research/non_existent_intelx_id")
    assert resp_404.status_code == 404
