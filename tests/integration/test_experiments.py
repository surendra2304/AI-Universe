"""Integration tests for Phase 9: BenchmarkHarness, Experiment Runner, and API endpoints."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.orchestrator import orchestrator
from app.experiments.harness import BenchmarkHarness
from app.main import app
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse


@pytest.fixture
def test_exp_env(tmp_path):
    test_db = str(tmp_path / "test_experiments_api.db")
    memory = SQLiteMemory(db_path=test_db)
    asyncio.run(memory.initialize())
    orchestrator.memory = memory
    harness = BenchmarkHarness(memory=memory, orchestrator=orchestrator)
    return memory, harness


@pytest.mark.asyncio
async def test_benchmark_harness_suite(test_exp_env):
    memory, harness = test_exp_env

    mock_llm_response = ProviderResponse(
        content="Modular architecture with sqlite persistence and decoupled agent identity.",
        model="gemini-2.5-pro",
        provider="gemini",
        total_tokens=60,
        latency_seconds=0.4
    )

    with patch("app.agents.debate.get_provider") as mock_debate_prov, \
         patch("app.providers.gemini.GeminiProvider.generate", new_callable=AsyncMock) as mock_gen:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_debate_prov.return_value = mock_prov
        mock_gen.return_value = mock_llm_response

        exp = await harness.run_benchmark_suite(benchmark_ids=["bench_001_arch"])
        assert exp.id.startswith("exp_bench_")
        assert exp.status == "completed"
        assert "detailed_cases" in exp.result
        assert len(exp.result["detailed_cases"]) == 1
        assert exp.result["detailed_cases"][0]["benchmark_id"] == "bench_001_arch"


@pytest.mark.asyncio
async def test_baseline_vs_debate_comparison(test_exp_env):
    memory, harness = test_exp_env

    mock_llm_response = ProviderResponse(
        content="Microservices introduce network latency and distributed state complexity compared to monoliths.",
        model="gemini-2.5-pro",
        provider="gemini",
        total_tokens=80,
        latency_seconds=0.5
    )

    with patch("app.agents.debate.get_provider") as mock_debate_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_debate_prov.return_value = mock_prov

        exp = await harness.run_baseline_vs_debate_comparison(
            question="Compare microservices vs monolithic architecture."
        )
        assert exp.id.startswith("exp_comp_")
        assert exp.status == "completed"
        assert "fast_baseline" in exp.result
        assert "multi_agent_debate" in exp.result


@pytest.mark.asyncio
async def test_experiments_api_endpoints(test_exp_env):
    memory, _ = test_exp_env

    mock_llm_response = ProviderResponse(
        content="Testing model comparison across providers.",
        model="gemini-2.5-flash",
        provider="gemini",
        total_tokens=40
    )

    with patch("app.agents.debate.get_provider") as mock_debate_prov:
        mock_prov = AsyncMock()
        mock_prov.provider_name = "mock_provider"
        mock_prov.generate.return_value = mock_llm_response
        mock_debate_prov.return_value = mock_prov

        with TestClient(app) as client:
            resp = client.post(
                "/experiments",
                json={
                    "experiment_type": "baseline_vs_debate",
                    "question": "What is the fastest key-value store?"
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"].startswith("exp_comp_")

            # Retrieve experiment by ID
            get_resp = client.get(f"/experiments/{data['id']}")
            assert get_resp.status_code == 200
            get_data = get_resp.json()
            assert get_data["id"] == data["id"]
            assert get_data["status"] == "completed"
