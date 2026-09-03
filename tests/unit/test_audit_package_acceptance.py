"""Acceptance & Regression Tests for the Consolidated Audit & Remediation Package."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.agents.adjudication import Adjudicator
from app.agents.base import Agent
from app.agents.reasoning import (
    EvidenceRelation,
    SpecialistAssessment,
)
from app.core.config import Settings
from app.core.dag import DAGNode, ExecutionDAG
from app.core.dag_executor import DAGExecutor
from app.main import app
from app.providers.errors import (
    AuthenticationError,
    RateLimitError,
    TemporaryUnavailableError,
    normalize_provider_exception,
)
from app.version import VERSION

client = TestClient(app)


def test_canonical_version_consistency():
    """Verify one canonical version is exposed across FastAPI, health, root, and version module."""
    assert VERSION == "2.0.0"
    assert app.version == VERSION

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["version"] == VERSION

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["version"] == VERSION


def test_insecure_default_key_rejected_when_not_configured():
    """Verify built-in 'inference_api' is rejected when no key is explicitly configured in settings."""
    unconfigured_settings = Settings(
        _env_file=None,
        INFERENCE_API_KEY=None,
        inference_api_KEY=None,
        FRIDAY_UNIVERSE_API_KEY=None,
        X_FRIDAY_API_KEY=None,
        FRIDAY_API_KEY=None,
        INSECURE_DEV_AUTH=False
    )
    assert unconfigured_settings.get_friday_api_key() is None


def test_global_exception_handler_safe_envelope():
    """Verify HTTP 500 does not leak Python exception class names."""
    with patch("app.health.agent_registry.list_agents", side_effect=ValueError("Secret internal db corruption")):
        res = client.get("/status")
        assert res.status_code == 500
        data = res.json()
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "correlation_id" in data
        assert "ValueError" not in str(data)
        assert "Secret internal db" not in str(data)


def test_typed_provider_error_normalization():
    """Verify provider exceptions normalize into typed errors with retryable flags."""
    err_429 = normalize_provider_exception(Exception("429 Too Many Requests"), provider="gemini")
    assert isinstance(err_429, RateLimitError)
    assert err_429.is_retryable() is True

    err_503 = normalize_provider_exception(Exception("503 Service Unavailable"), provider="groq")
    assert isinstance(err_503, TemporaryUnavailableError)
    assert err_503.is_retryable() is True

    err_auth = normalize_provider_exception(Exception("401 Unauthorized API Key"), provider="mistral")
    assert isinstance(err_auth, AuthenticationError)
    assert err_auth.is_retryable() is False


def test_adjudicator_confidence_and_claims_extraction():
    """Verify atomic claim extraction, structured evidence generation, and calibrated confidence calculation."""
    dummy_agent = Agent(
        id="architect",
        name="System Architect",
        role="System Architect",
        purpose="Architectural trade-offs",
        system_instructions="Architecture advice",
        model_provider="gemini",
        model_name="gemini-3.7-flash"
    )

    text = (
        "- Deploy SQLite in WAL mode to achieve 15000 req/sec benchmark throughput.\n"
        "- Concurrency limiter prevents cross-loop deadlock exceptions."
    )

    claims, evidence = Adjudicator.extract_claims_and_evidence(dummy_agent, "gemini-3.7-flash", text)
    assert len(claims) >= 2
    assert len(evidence) >= 1
    assert evidence[0].relation == EvidenceRelation.SUPPORTS

    assessment = SpecialistAssessment(
        agent_id="architect",
        agent_role="System Architect",
        summary=text,
        claims=claims,
        evidence=evidence,
        model_confidence=0.95
    )

    calib_conf, factors = Adjudicator.calculate_system_confidence([assessment], contradictions=[], evidence_count=len(evidence), complexity_str="simple")
    assert 0.20 <= calib_conf <= 1.0
    assert factors["total_evidence_pieces"] >= 1


@pytest.mark.asyncio
async def test_dag_executor_concurrency_and_cancellation():
    """Verify DAG Executor handles dependencies, concurrency, and cancellation tokens."""
    dag = ExecutionDAG()
    node1 = DAGNode(node_id="n1", agent_id="a1", agent_role="R1", dependencies=[])
    node2 = DAGNode(node_id="n2", agent_id="a2", agent_role="R2", dependencies=[])
    node3 = DAGNode(node_id="n3", agent_id="a3", agent_role="R3", dependencies=["n1", "n2"])

    dag.add_node(node1)
    dag.add_node(node2)
    dag.add_node(node3)

    cancel_event = asyncio.Event()
    executor = DAGExecutor(dag=dag, cancellation_event=cancel_event)

    async def mock_runner(node: DAGNode, deps: dict):
        return f"done_{node.node_id}"

    results = await executor.execute(mock_runner)
    assert results["n1"].status == "completed"
    assert results["n2"].status == "completed"
    assert results["n3"].status == "completed"
    assert results["n3"].output == "done_n3"

    # Test Cancellation
    cancel_event.set()
    executor_cancelled = DAGExecutor(dag=dag, cancellation_event=cancel_event)
    results_cancelled = await executor_cancelled.execute(mock_runner)
    assert results_cancelled["n1"].status == "cancelled"
