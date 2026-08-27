"""Tests for Software Engineering Specialists and Unified Provider Manager."""

import pytest
from fastapi.testclient import TestClient

from app.agents.registry import agent_registry
from app.agents.software_specialists import get_software_specialist_agents
from app.main import app
from app.providers.unified_manager import UnifiedExecutionRequest, unified_provider_manager

client = TestClient(app)


def test_software_specialist_agents_registered():
    """Verifies all 7 FORGE software engineering specialists are registered with appropriate strengths."""
    specialists = get_software_specialist_agents()
    assert len(specialists) == 7

    agent_ids = [a.id for a in specialists]
    assert "requirements_analyst" in agent_ids
    assert "system_architect" in agent_ids
    assert "code_generator" in agent_ids
    assert "code_reviewer" in agent_ids
    assert "test_generator" in agent_ids
    assert "documentation_writer" in agent_ids
    assert "devops_engineer" in agent_ids

    # Check registry discovery
    arch_agent = agent_registry.get_agent("system_architect")
    assert arch_agent is not None
    assert arch_agent.role == "System Architect"


@pytest.mark.asyncio
async def test_unified_provider_manager_execution():
    """Tests execution across unified manager for trading and coding roles."""
    # Test trading role
    req_trade = UnifiedExecutionRequest(
        provider="auto",
        agent_role="trading_analyst",
        prompt="Analyze drawdown on BTCUSDT with 3 consecutive losses",
        context={"symbol": "BTCUSDT", "drawdown_pct": 4.2}
    )
    resp_trade = await unified_provider_manager.execute(req_trade)
    assert resp_trade.agent_role == "trading_analyst"
    assert resp_trade.content is not None
    assert resp_trade.latency_ms > 0

    # Test software engineering role
    req_code = UnifiedExecutionRequest(
        provider="auto",
        agent_role="code_generator",
        prompt="Write a Python function for calculating exponential moving average",
        max_tokens=500
    )
    resp_code = await unified_provider_manager.execute(req_code)
    assert resp_code.agent_role == "code_generator"
    assert resp_code.status in ("success", "fallback_success")


def test_providers_execute_api_endpoint():
    """Tests POST /v1/providers/execute endpoint."""
    payload = {
        "provider": "auto",
        "agent_role": "system_architect",
        "prompt": "Design a high-throughput microservices architecture for real-time telemetry",
        "context": {"throughput_rps": 5000},
        "max_tokens": 1000,
        "temperature": 0.7
    }
    resp = client.post("/v1/providers/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "provider_used" in data
    assert "model_used" in data
    assert data["agent_role"] == "system_architect"
    assert "content" in data
    assert data["status"] in ("success", "fallback_success")
