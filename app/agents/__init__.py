"""Agents package initialization."""

from app.agents.base import Agent, BaseAgentRegistry
from app.agents.registry import agent_registry, InMemoryAgentRegistry
from app.agents.roles import get_all_specialist_agents, register_all_specialists
from app.agents.router import router, TaskRouter

__all__ = [
    "Agent",
    "BaseAgentRegistry",
    "agent_registry",
    "InMemoryAgentRegistry",
    "get_all_specialist_agents",
    "register_all_specialists",
    "router",
    "TaskRouter",
]
