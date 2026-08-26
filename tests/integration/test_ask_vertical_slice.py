"""Integration test suite for the end-to-end /ask vertical slice."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.orchestrator import orchestrator
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest.fixture
def client_with_test_db(tmp_path):
    test_db_path = str(tmp_path / "test_universe.db")
    test_memory = SQLiteMemory(db_path=test_db_path)
    orchestrator.memory = test_memory

    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_ask_endpoint_fast_mode(client_with_test_db):
    client = client_with_test_db

    mock_llm_response = ProviderResponse(
        content="Antigravity is an advanced agentic AI coding framework.",
        model="gemini-2.5-flash",
        provider="gemini",
        prompt_tokens=20,
        completion_tokens=10,
        total_tokens=30,
        latency_seconds=0.45
    )

    with patch("app.agents.debate.model_gateway.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_llm_response

        response = client.post(
            "/ask",
            json={
                "question": "What is Antigravity?",
                "mode": "auto"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "Antigravity" in data["answer"]
        # CollaborationEngine returns "consensus" or "debate" — not the raw routing mode
        assert data["mode_used"] in ["consensus", "debate", "collaboration", "fast"]
        assert data["task_id"].startswith("task_")
        assert data["run_id"].startswith("deb_")
        assert data["confidence"] > 0.8

        # Verify task is queryable via GET /tasks/{id}
        task_resp = client.get(f"/tasks/{data['task_id']}")
        assert task_resp.status_code == 200
        task_data = task_resp.json()
        assert task_data["id"] == data["task_id"]
        assert task_data["status"] == "completed"


@pytest.mark.asyncio
async def test_ask_endpoint_complex_debate_routing(client_with_test_db):
    client = client_with_test_db

    mock_llm_response = ProviderResponse(
        content="Evaluating architecture trade-offs between monolithic vs microservices...",
        model="gemini-2.5-flash",
        provider="gemini",
        total_tokens=50
    )

    with patch("app.agents.debate.model_gateway.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_llm_response

        response = client.post(
            "/ask",
            json={
                "question": "Compare the architecture trade-offs of microservices vs monoliths.",
                "mode": "auto"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode_used"] in ["debate", "consensus", "collaboration"]


@pytest.mark.asyncio
async def test_ask_empty_question_validation(client_with_test_db):
    client = client_with_test_db
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400
    assert "Question cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_task(client_with_test_db):
    client = client_with_test_db
    response = client.get("/tasks/non_existent_task_999")
    assert response.status_code == 404
