"""Unit tests for the 10 Specialist Agent Roles and Registry."""

import pytest
from app.agents.registry import agent_registry
from app.agents.roles import get_all_specialist_agents, register_all_specialists

EXPECTED_ROLES = [
    "researcher",
    "architect",
    "coder",
    "debugger",
    "security_analyst",
    "data_analyst",
    "critic",
    "fact_checker",
    "strategist",
    "synthesizer"
]


def test_specialist_agents_definition():
    agents = get_all_specialist_agents()
    assert len(agents) == 10
    agent_ids = [a.id for a in agents]
    for expected_id in EXPECTED_ROLES:
        assert expected_id in agent_ids


def test_agent_registry_contains_all_10_specialists():
    register_all_specialists()
    registered = agent_registry.list_agents()
    assert len(registered) >= 10

    for expected_id in EXPECTED_ROLES:
        agent = agent_registry.get_agent(expected_id)
        assert agent is not None, f"Agent {expected_id} not found in registry."
        assert agent.id == expected_id
        assert len(agent.name) > 0
        assert len(agent.role) > 0
        assert len(agent.purpose) > 0
        assert len(agent.system_instructions) > 20
        assert agent.model_provider == "gemini"
        assert len(agent.strengths) > 0
        assert agent.status == "active"


def test_agent_capability_lookup():
    register_all_specialists()

    threat_agents = agent_registry.get_agents_by_capability("threat")
    assert any(a.id == "security_analyst" for a in threat_agents)

    debug_agents = agent_registry.get_agents_by_capability("deadlock")
    assert any(a.id == "debugger" for a in debug_agents)

    code_agents = agent_registry.get_agents_by_capability("refactoring")
    assert any(a.id == "coder" for a in code_agents)
