"""Integration tests for Phase 11: FRIDAY Peer Integration and Security Boundary."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.orchestrator import orchestrator
from app.main import app
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest.fixture
def friday_client(tmp_path):
    test_db = str(tmp_path / "test_friday_integration.db")
    memory = SQLiteMemory(db_path=test_db)
    orchestrator.memory = memory
    settings.FRIDAY_API_KEY = "test_friday_secret_key_12345"

    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_friday_ask_authenticated(friday_client):
    client = friday_client

    mock_llm_response = ProviderResponse(
        content="FRIDAY consultation: Recommended architecture strategy validated.",
        model="gemini-2.5-flash",
        provider="gemini",
        total_tokens=45,
        latency_seconds=0.35
    )

    with patch("app.providers.gemini.GeminiProvider.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_response

        headers = {"X-FRIDAY-API-Key": "test_friday_secret_key_12345"}
        resp = client.post(
            "/v1/friday/ask",
            headers=headers,
            json={
                "question": "Assess memory isolation risks for FRIDAY subagents.",
                "caller_id": "friday_executive",
                "max_latency": 10.0
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"].startswith("task_")
        assert "FRIDAY consultation" in data["answer"]
        assert data["confidence"] > 0.8
        assert data["provenance"]["caller_id"] == "friday_executive"
        assert data["provenance"]["platform"] == "AI Universe"


@pytest.mark.asyncio
async def test_friday_debate_provenance_and_dissent(friday_client):
    client = friday_client

    mock_llm_response = ProviderResponse(
        content="FRIDAY debate consensus: Enforce cryptographic capabilities across process boundaries.",
        model="gemini-2.5-pro",
        provider="gemini",
        total_tokens=95,
        latency_seconds=0.60
    )

    with patch("app.agents.debate.get_provider") as mock_get_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_get_prov.return_value = mock_prov

        headers = {"X-FRIDAY-API-Key": "test_friday_secret_key_12345"}
        resp = client.post(
            "/v1/friday/debate",
            headers=headers,
            json={
                "question": "Should FRIDAY deploy untrusted plugins inside separate sandbox workers?",
                "caller_id": "friday_security_core"
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode_used"] in ["debate", "consensus", "collaboration"]
        assert data["confidence"] >= 0.85
        assert isinstance(data["unresolved_disagreements"], list)
        assert len(data["key_evidence"]) > 0
        assert data["provenance"]["rounds_completed"] in [2, 6]
        assert data["provenance"]["caller_id"] == "friday_security_core"


@pytest.mark.asyncio
async def test_friday_authentication_failure_missing_header(friday_client):
    client = friday_client
    # No header provided
    resp = client.post("/v1/friday/ask", json={"question": "Test unauthorized inquiry"})
    assert resp.status_code == 401
    assert "Missing 'X-FRIDAY-API-Key'" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_friday_authentication_failure_invalid_key(friday_client):
    client = friday_client
    headers = {"X-FRIDAY-API-Key": "invalid_wrong_secret_key"}
    resp = client.post("/v1/friday/ask", headers=headers, json={"question": "Test forbidden inquiry"})
    assert resp.status_code == 403
    assert "Forbidden: Invalid FRIDAY API Key" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_friday_status_endpoint(friday_client):
    client = friday_client
    headers = {"X-FRIDAY-API-Key": "test_friday_secret_key_12345"}

    # Test authenticated request
    resp = client.get("/v1/friday/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Validate schema fields
    assert "active_agents" in data
    assert "configured_providers" in data
    assert "available_models" in data

    # Validate active agent roles list
    assert isinstance(data["active_agents"], list)
    assert len(data["active_agents"]) == 10
    assert "Architect" in data["active_agents"]
    assert "Coder" in data["active_agents"]
    assert "Critic" in data["active_agents"]

    # Validate configured providers & models
    assert isinstance(data["configured_providers"], list)
    assert isinstance(data["available_models"], list)
    assert len(data["available_models"]) > 0

    # Test unauthorized request (missing header)
    unauth_resp = client.get("/v1/friday/status")
    assert unauth_resp.status_code == 401
