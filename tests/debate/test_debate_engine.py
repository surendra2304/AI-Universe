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
async def test_consensus_first_execution_path(debate_env):
    """Verify that if specialists agree (CONSENSUS_REACHED: YES), rounds 2-6 are skipped and mode_used is consensus."""
    engine, memory = debate_env

    # Provider returns consensus agreement check
    def mock_generate_consensus(req):
        if "CONSENSUS_REACHED:" in req.system_instruction or "Evaluate whether these specialist analyses" in req.messages[0].content:
            return ProviderResponse(
                content="CONSENSUS_REACHED: YES\nALIGNMENT_SUMMARY: All specialists agree on using a lock-free modular monolith.",
                model="meta/llama-3.1-8b-instruct",
                provider="nvidia"
            )
        return ProviderResponse(
            content="Specialist analysis recommending modular monolith pattern.",
            model="gemini-3.6-flash",
            provider="gemini"
        )

    with patch("app.agents.debate.get_provider") as mock_get_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.side_effect = mock_generate_consensus
        mock_get_prov.return_value = mock_prov

        agents = [
            agent_registry.get_agent("architect"),
            agent_registry.get_agent("security_analyst"),
            agent_registry.get_agent("coder")
        ]

        result = await engine.run_debate(
            task_id="task_consensus_001",
            question="Should a low-latency trading engine use a modular monolith?",
            participating_agents=agents
        )

        assert result.debate_id.startswith("deb_")
        assert result.task_id == "task_consensus_001"
        assert result.mode_used == "consensus"
        assert result.confidence >= 0.90
        assert len(result.unresolved_disagreements) == 0
        assert len(result.rounds) == 3  # Round 0 (Framing), Round 1 (Analysis), Round 5 (Consensus Synthesis)


@pytest.mark.asyncio
async def test_full_debate_disagreement_path(debate_env):
    """Verify that if disagreement is detected (CONSENSUS_REACHED: NO), the full 6-round debate protocol executes."""
    engine, memory = debate_env

    def mock_generate_disagreement(req):
        if "CONSENSUS_REACHED:" in req.system_instruction or "Evaluate whether these specialist analyses" in req.messages[0].content:
            return ProviderResponse(
                content="CONSENSUS_REACHED: NO\nALIGNMENT_SUMMARY: Severe conflict between Architect (monolith) and Security Analyst (isolated services).",
                model="meta/llama-3.1-8b-instruct",
                provider="nvidia"
            )
        return ProviderResponse(
            content="Adversarial critique / specialist rebuttal output.",
            model="gemini-3.6-flash",
            provider="gemini"
        )

    with patch("app.agents.debate.get_provider") as mock_get_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.side_effect = mock_generate_disagreement
        mock_get_prov.return_value = mock_prov

        agents = [
            agent_registry.get_agent("architect"),
            agent_registry.get_agent("security_analyst"),
            agent_registry.get_agent("critic")
        ]

        result = await engine.run_debate(
            task_id="task_debate_002",
            question="Microservices vs Modular Monolith under adversarial threat models?",
            participating_agents=agents
        )

        assert result.debate_id.startswith("deb_")
        assert result.task_id == "task_debate_002"
        assert result.mode_used == "debate"
        assert len(result.rounds) == 7  # Round 0 through Round 6
        assert result.confidence > 0.8
        assert len(result.unresolved_disagreements) > 0


@pytest.mark.asyncio
async def test_fastapi_debate_endpoint(tmp_path):
    test_db = str(tmp_path / "test_api_debate.db")
    test_memory = SQLiteMemory(db_path=test_db)
    await test_memory.initialize()
    orchestrator.memory = test_memory

    mock_llm_response = ProviderResponse(
        content="CONSENSUS_REACHED: NO\nSynthesized debate decision: Use capability-based security boundaries.",
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
            assert data["mode_used"] in ["debate", "consensus"]
            assert data["confidence"] > 0.8
            assert len(data["agents_used"]) == 4
