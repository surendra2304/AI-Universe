"""Unit and mock tests for the 6-Round Structured Debate Engine."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.agents.debate import DebateEngine
from app.agents.registry import agent_registry
from app.agents.roles import register_all_specialists
from app.core.orchestrator import orchestrator
from app.main import app
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest_asyncio.fixture
async def debate_env(tmp_path):
    register_all_specialists()
    test_db = str(tmp_path / "test_debate.db")
    memory = SQLiteMemory(db_path=test_db)
    await memory.initialize()
    engine = DebateEngine(memory=memory, registry=agent_registry)
    return engine, memory


@pytest.mark.asyncio
async def test_6_round_debate_execution(debate_env):
    engine, memory = debate_env

    mock_llm_response = ProviderResponse(
        content="Simulated debate output for the given stage.",
        model="gemini-2.5-pro",
        provider="gemini",
        prompt_tokens=50,
        completion_tokens=25,
        total_tokens=75,
        latency_seconds=0.3
    )

    with patch("app.agents.debate.get_provider") as mock_get_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_get_prov.return_value = mock_prov

        agents = [
            agent_registry.get_agent("architect"),
            agent_registry.get_agent("security_analyst"),
            agent_registry.get_agent("critic")
        ]

        result = await engine.run_debate(
            task_id="task_debate_001",
            question="What is the safest architectural pattern for autonomous agent tool execution?",
            participating_agents=agents
        )

        assert result.debate_id.startswith("deb_")
        assert result.task_id == "task_debate_001"
        assert len(result.rounds) == 7  # Round 0 through Round 6
        assert result.confidence > 0.8
        assert len(result.unresolved_disagreements) > 0
        assert len(result.key_evidence) > 0

        # Verify rounds structure
        round_numbers = [r.round_number for r in result.rounds]
        assert round_numbers == [0, 1, 2, 3, 4, 5, 6]

        # Verify Round 1 had independent messages from all participating agents
        r1_log = next(r for r in result.rounds if r.round_number == 1)
        assert len(r1_log.messages) == len(agents)

        # Verify messages persisted in SQLite database
        saved_messages = await memory.get_task_messages("task_debate_001")
        assert len(saved_messages) > 0


@pytest.mark.asyncio
async def test_fastapi_debate_endpoint(tmp_path):
    test_db = str(tmp_path / "test_api_debate.db")
    test_memory = SQLiteMemory(db_path=test_db)
    await test_memory.initialize()
    orchestrator.memory = test_memory

    mock_llm_response = ProviderResponse(
        content="Synthesized debate decision: Use capability-based security boundaries.",
        model="gemini-2.5-pro",
        provider="gemini",
        prompt_tokens=40,
        completion_tokens=30,
        total_tokens=70
    )

    with patch("app.agents.debate.get_provider") as mock_get_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_get_prov.return_value = mock_prov

        with TestClient(app) as client:
            resp = client.post(
                "/debate",
                json={
                    "question": "Should AI Universe use microservices or modular monolith?",
                    "max_agents": 4
                }
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["mode_used"] == "debate"
            assert "Synthesized debate decision" in data["answer"]
            assert data["confidence"] > 0.8
            assert len(data["unresolved_disagreements"]) > 0
            assert len(data["agents_used"]) == 4
