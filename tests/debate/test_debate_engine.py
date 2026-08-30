"""Unit and mock tests for the Real-Time Multi-Agent Collaboration Engine."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.agents.debate import CollaborationEngine, DebateEngine
from app.agents.registry import agent_registry
from app.agents.roles import register_all_specialists
from app.core.orchestrator import orchestrator
from app.main import app
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest_asyncio.fixture
async def collab_env(tmp_path):
    register_all_specialists()
    test_db = str(tmp_path / "test_collab.db")
    memory = SQLiteMemory(db_path=test_db)
    await memory.initialize()
    engine = CollaborationEngine(memory=memory, registry=agent_registry)
    return engine, memory


@pytest.mark.asyncio
async def test_parallel_collaboration_instant_synthesis(collab_env):
    """Verify parallel specialist perspectives run via asyncio.gather and merge instantly."""
    engine, memory = collab_env

    async def mock_execute(provider_name, request, **kwargs):
        if "Consensus Synthesizer" in (request.system_instruction or "") or "evaluate the specialist proposals" in request.messages[0].content:
            return ProviderResponse(
                content="Unified Consensus: Deploy a lock-free modular monolith with strict domain boundaries.",
                model="command-r7b-12-2024",
                provider="cohere"
            )
        return ProviderResponse(
            content="Specialist analysis recommending modular monolith design for high throughput.",
            model="gemini-3.6-flash",
            provider="gemini"
        )

    with patch("app.agents.debate.model_gateway.execute", side_effect=mock_execute):
        agents = [
            agent_registry.get_agent("architect"),
            agent_registry.get_agent("security_analyst"),
            agent_registry.get_agent("coder")
        ]

        result = await engine.run_collaboration(
            task_id="task_collab_001",
            question="Should a high-frequency trading platform use a modular monolith?",
            participating_agents=agents
        )

        assert result.debate_id.startswith("deb_")
        assert result.task_id == "task_collab_001"
        assert result.mode_used == "consensus"
        assert result.confidence >= 0.90
        assert len(result.unresolved_disagreements) == 0
        assert len(result.rounds) == 2  # Round 1 (Parallel Perspectives), Round 2 (Consensus Synthesis)
        assert "Unified Consensus" in result.final_answer


@pytest.mark.asyncio
async def test_targeted_rebuttal_on_severe_conflict(collab_env):
    """Verify that when the Synthesizer detects CONFLICT_DETECTED, a targeted Rebuttal triggers."""
    engine, memory = collab_env

    async def mock_execute_conflict(provider_name, request, **kwargs):
        content_query = request.messages[0].content
        if "evaluate the specialist proposals" in content_query:
            return ProviderResponse(
                content="CONFLICT_DETECTED: Fundamental architectural clash between Architect (shared memory) and Security Analyst (process sandboxing).",
                model="command-r7b-12-2024",
                provider="cohere"
            )
        elif "Adversarial Critic" in (request.system_instruction or "") or "challenge the conflicting assumptions" in content_query:
            return ProviderResponse(
                content="Adversarial Red Team: Sandboxing is required for untrusted modules; internal modules can share memory.",
                model="gemini-3.5-flash",
                provider="gemini"
            )
        elif "final, conclusive architectural recommendation" in content_query:
            return ProviderResponse(
                content="Final Resolution: Hybrid architecture combining shared-memory core with isolated sandboxes for untrusted plugins.",
                model="command-r7b-12-2024",
                provider="cohere"
            )
        return ProviderResponse(
            content="Initial specialist recommendation.",
            model="gemini-3.6-flash",
            provider="gemini"
        )

    with patch("app.agents.debate.model_gateway.execute", side_effect=mock_execute_conflict):
        agents = [
            agent_registry.get_agent("architect"),
            agent_registry.get_agent("security_analyst"),
            agent_registry.get_agent("critic")
        ]

        result = await engine.run_collaboration(
            task_id="task_conflict_002",
            question="Untrusted plugin security model?",
            participating_agents=agents
        )

        assert result.debate_id.startswith("deb_")
        assert result.task_id == "task_conflict_002"
        assert result.mode_used == "debate"
        assert len(result.rounds) == 3  # Round 1 (Parallel), Round 3 (Rebuttal), Round 4 (Final Resolution)
        assert "Final Resolution" in result.final_answer


@pytest.mark.asyncio
async def test_fastapi_debate_endpoint_collaboration(tmp_path):
    test_db = str(tmp_path / "test_api_collab.db")
    test_memory = SQLiteMemory(db_path=test_db)
    await test_memory.initialize()
    orchestrator.memory = test_memory

    mock_llm_response = ProviderResponse(
        content="Synthesized collaborative decision: Modular monolith with fine-grained capability isolation.",
        model="gemini-2.5-pro",
        provider="gemini",
        prompt_tokens=40,
        completion_tokens=30,
        total_tokens=70
    )

    with patch("app.agents.debate.model_gateway.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_llm_response

        with TestClient(app) as client:
            resp = client.post(
                "/debate",
                json={
                    "question": "Should Inference use microservices or modular monolith?",
                    "max_agents": 4
                }
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["mode_used"] in ["debate", "consensus", "collaboration"]
            assert data["confidence"] > 0.8
            assert len(data["agents_used"]) == 4
