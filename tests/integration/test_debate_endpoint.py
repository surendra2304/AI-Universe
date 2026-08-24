"""Integration tests for the /debate FastAPI endpoint and Orchestrator debate workflow."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.orchestrator import orchestrator
from app.main import app
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest.fixture
def client_with_test_db(tmp_path):
    test_db_path = str(tmp_path / "test_debate_endpoint.db")
    test_memory = SQLiteMemory(db_path=test_db_path)
    orchestrator.memory = test_memory

    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_debate_endpoint_end_to_end(client_with_test_db):
    client = client_with_test_db

    mock_llm_response = ProviderResponse(
        content="Debate consensus: Adopt an asynchronous event-driven modular architecture.",
        model="gemini-2.5-pro",
        provider="gemini",
        prompt_tokens=45,
        completion_tokens=25,
        total_tokens=70,
        latency_seconds=0.35
    )

    with patch("app.providers.gemini.GeminiProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_response

        response = client.post(
            "/debate",
            json={
                "question": "What is the optimal persistence architecture for high-frequency trading logs?",
                "max_agents": 4,
                "require_evidence": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"].startswith("task_")
        assert data["run_id"].startswith("deb_")
        assert "Debate consensus" in data["answer"]
        assert len(data["agents_used"]) == 4
        assert len(data["models_used"]) == 4
        assert 0.0 <= data["confidence"] <= 1.0
        assert isinstance(data["unresolved_disagreements"], list)
        assert len(data["unresolved_disagreements"]) > 0
        assert data["total_tokens"] > 0
        assert data["latency_seconds"] >= 0.0

        # Verify task is queryable and completed in SQLite
        task_resp = client.get(f"/tasks/{data['task_id']}")
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        assert task_data["id"] == data["task_id"]
        assert task_data["status"] == "completed"
        assert task_data["mode"] == "debate"
        assert task_data["confidence"] == data["confidence"]


@pytest.mark.asyncio
async def test_debate_endpoint_empty_question(client_with_test_db):
    client = client_with_test_db
    response = client.post("/debate", json={"question": "   "})
    assert response.status_code == 400
    assert "Question cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_debate_endpoint_invalid_max_agents(client_with_test_db):
    client = client_with_test_db
    response = client.post("/debate", json={"question": "Valid question?", "max_agents": 1})
    assert response.status_code == 422  # Pydantic validation error (ge=2)
