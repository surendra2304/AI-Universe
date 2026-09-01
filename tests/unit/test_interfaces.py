"""Unit tests for Core Foundation abstract interfaces and data contracts."""

from app.agents.base import Agent
from app.agents.registry import InMemoryAgentRegistry
from app.core.orchestrator import OrchestrationRequest
from app.evaluation.evaluator import EvaluationReport, EvaluationScore
from app.memory.base import MemoryRecord, TaskRecord
from app.providers.base import ProviderMessage, ProviderRequest, ProviderResponse


def test_provider_models():
    msg = ProviderMessage(role="user", content="Hello test")
    assert msg.role == "user"

    req = ProviderRequest(messages=[msg], temperature=0.5)
    assert req.temperature == 0.5
    assert len(req.messages) == 1

    resp = ProviderResponse(
        content="Response text",
        model="gemini-2.5-flash",
        provider="gemini",
        total_tokens=42
    )
    assert resp.content == "Response text"
    assert resp.total_tokens == 42


def test_agent_model_and_registry():
    agent = Agent(
        id="architect",
        name="Chief Architect",
        role="Architect",
        purpose="Design modular system architectures",
        system_instructions="Think systematically and define clear boundaries.",
        allowed_tools=["read_doc"],
        model_provider="gemini",
        model_name="gemini-2.5-flash",
        strengths=["system design", "modularity"],
        weaknesses=["shallow factual trivia"]
    )
    assert agent.id == "architect"
    assert "system design" in agent.strengths

    registry = InMemoryAgentRegistry()
    registry.register_agent(agent)

    retrieved = registry.get_agent("architect")
    assert retrieved is not None
    assert retrieved.name == "Chief Architect"

    matched = registry.get_agents_by_capability("modularity")
    assert len(matched) == 1
    assert matched[0].id == "architect"


def test_memory_models():
    mem = MemoryRecord(
        id="mem_123",
        agent_id="architect",
        content="Prefers explicit boundaries over implicit conventions."
    )
    assert mem.agent_id == "architect"
    assert mem.memory_type == "fact"

    task = TaskRecord(id="task_123", question="How to design multi-agent systems?")
    assert task.status == "pending"


def test_orchestrator_and_evaluator_models():
    orch_req = OrchestrationRequest(question="Test question?", mode="debate")
    assert orch_req.mode == "debate"

    eval_score = EvaluationScore(
        criterion="correctness",
        score=0.95,
        reasoning="Claims match verified technical documentation."
    )
    report = EvaluationReport(
        run_id="run_123",
        overall_score=0.92,
        scores=[eval_score],
        confidence=0.9
    )
    assert report.overall_score == 0.92
    assert len(report.scores) == 1
