"""Integration and Unit tests for Dynamic DAG Orchestration, Complexity Dispatch, and Health-Aware Routing."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.dag import DAGNode, ExecutionDAG, TaskComplexity, classify_task_complexity
from app.core.orchestrator import OrchestrationRequest, Orchestrator
from app.memory.sqlite import SQLiteMemory
from app.providers.base import ProviderResponse
from app.providers.health import provider_health_tracker
from app.agents.registry import agent_registry


@pytest.fixture
def dag_env(tmp_path):
    test_db = str(tmp_path / "test_dag.db")
    memory = SQLiteMemory(db_path=test_db)
    orch = Orchestrator(memory=memory)
    return orch, memory


def test_task_complexity_classifier():
    """Verify task complexity classification into SIMPLE, COMPLEX, and STRATEGIC."""
    # Fast mode or short greeting -> SIMPLE
    assert classify_task_complexity("hello", requested_mode="fast") == TaskComplexity.SIMPLE
    assert classify_task_complexity("what is the time?", requested_mode="auto") == TaskComplexity.SIMPLE

    # Coding / Debugging -> COMPLEX
    assert classify_task_complexity("Implement a Python function to refactor async pipelines", requested_mode="auto") == TaskComplexity.COMPLEX
    assert classify_task_complexity("Debug this deadlock in the thread pool", requested_mode="auto") == TaskComplexity.COMPLEX

    # Architectural / Trade-offs -> STRATEGIC
    assert classify_task_complexity("Compare microservices vs monolith architecture for high scale", requested_mode="auto") == TaskComplexity.STRATEGIC
    assert classify_task_complexity("Evaluate security threat models for authentication", requested_mode="debate") == TaskComplexity.STRATEGIC


def test_execution_dag_topological_sort():
    """Verify Directed Acyclic Graph constructs parallel independent layers."""
    dag = ExecutionDAG()
    dag.add_node(DAGNode(node_id="node_architect", agent_id="architect", agent_role="Architect", dependencies=[]))
    dag.add_node(DAGNode(node_id="node_security", agent_id="security_analyst", agent_role="Security Analyst", dependencies=[]))
    dag.add_node(DAGNode(node_id="node_coder", agent_id="coder", agent_role="Coder", dependencies=[]))
    dag.add_node(DAGNode(
        node_id="node_synthesizer",
        agent_id="synthesizer",
        agent_role="Synthesizer",
        dependencies=["node_architect", "node_security", "node_coder"]
    ))

    layers = dag.build_layers()
    assert len(layers) == 2
    # Layer 0: all 3 independent agents
    assert set(layers[0]) == {"node_architect", "node_security", "node_coder"}
    # Layer 1: Synthesizer dependent on Layer 0
    assert layers[1] == ["node_synthesizer"]


@pytest.mark.asyncio
async def test_easy_task_triggers_single_model_call_per_agent(dag_env):
    """Verify that an EASY / SIMPLE task only invokes the primary (1st) model for each agent."""
    orch, memory = dag_env
    await memory.initialize()

    called_models = []

    async def mock_execute(provider_name, request, **kwargs):
        called_models.append((provider_name, request.model))
        return ProviderResponse(
            content=f"Fast output from {provider_name}/{request.model}",
            model=request.model,
            provider=provider_name
        )

    with patch("app.agents.debate.model_gateway.execute", side_effect=mock_execute):
        req = OrchestrationRequest(
            question="What is 2 + 2?",
            mode="fast",
            max_agents=2
        )
        res = await orch.process_task(req)

        assert res.complexity == "simple"
        assert res.task_id.startswith("task_")
        # In fast mode, each participating agent (2 agents: specialist + synthesizer) invokes 1 model
        assert len(called_models) == 2


@pytest.mark.asyncio
async def test_complex_task_triggers_parallel_models_and_synthesis(dag_env):
    """Verify that a COMPLEX / STRATEGIC task queries top models in parallel per agent and for synthesizer."""
    orch, memory = dag_env
    await memory.initialize()

    called_models = []

    async def mock_execute(provider_name, request, **kwargs):
        called_models.append((provider_name, request.model))
        return ProviderResponse(
            content=f"Analysis from {provider_name} model {request.model}",
            model=request.model,
            provider=provider_name
        )

    with patch("app.agents.debate.model_gateway.execute", side_effect=mock_execute):
        req = OrchestrationRequest(
            question="Compare microservices vs monolith architecture for high scale high-frequency trade systems.",
            mode="auto",
            max_agents=3
        )
        res = await orch.process_task(req)

        assert res.complexity == "strategic"
        assert len(called_models) > 3  # Multiple models triggered across agents and synthesizer
        assert res.confidence > 0.8
        assert "Analysis from" in res.answer


@pytest.mark.asyncio
async def test_health_monitor_skips_rate_limited_provider(dag_env):
    """Verify that if Provider A is rate-limited/unhealthy, the orchestrator skips it and uses Provider B."""
    orch, memory = dag_env
    await memory.initialize()

    # Simulate provider_health_tracker flagging Gemini as unhealthy with 429
    provider_health_tracker.record_failure("gemini", error="429 Resource Exhausted", is_429=True)
    provider_health_tracker.record_failure("gemini", error="429 Resource Exhausted", is_429=True)
    provider_health_tracker.record_failure("gemini", error="429 Resource Exhausted", is_429=True)

    executed_providers = []

    async def mock_execute(provider_name, request, **kwargs):
        executed_providers.append(provider_name)
        return ProviderResponse(
            content=f"Healthy fallback answer from {provider_name}",
            model=request.model,
            provider=provider_name
        )

    with patch("app.agents.debate.model_gateway.execute", side_effect=mock_execute):
        # Researcher has models: [gemini, openrouter, cohere]
        # Since Gemini is unhealthy, researcher should skip Gemini and invoke OpenRouter / Cohere
        req = OrchestrationRequest(
            question="Explain quantum computing basics.",
            mode="fast"
        )
        res = await orch.process_task(req)

        assert res.task_id.startswith("task_")
        assert "gemini" not in executed_providers
        # Reset health tracker for other tests
        provider_health_tracker._stats.clear()
