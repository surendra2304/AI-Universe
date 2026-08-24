"""Base data models and contracts for AI Universe agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Pydantic model representing an individual specialist agent identity."""
    id: str = Field(description="Unique agent identifier, e.g., 'researcher', 'architect'")
    name: str = Field(description="Human-readable agent display name")
    role: str = Field(description="Primary specialist role title")
    purpose: str = Field(description="Core purpose and mission of the agent")
    system_instructions: str = Field(description="Base prompt/system instructions guiding reasoning")
    allowed_tools: List[str] = Field(default_factory=list, description="List of tools the agent is permitted to call")
    model_provider: str = Field(default="gemini", description="Underlying provider (gemini, groq, cerebras, etc.)")
    model_name: str = Field(default="gemini-2.5-flash", description="Provider model identifier")
    personality_style: Optional[str] = Field(default=None, description="Optional reasoning or interaction style")
    strengths: List[str] = Field(default_factory=list, description="Key domain capabilities and strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Known limitations or failure modes")
    memory_scope: str = Field(default="agent_private", description="Memory visibility: agent_private or shared")
    status: str = Field(default="active", description="Operational status: active, paused, deprecated")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional custom properties")


class BaseAgentRegistry(ABC):
    """Abstract interface for agent registration and discovery."""

    @abstractmethod
    def register_agent(self, agent: Agent) -> None:
        """Register a new specialist agent or update an existing one."""
        pass

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Retrieve an agent by its unique identifier."""
        pass

    @abstractmethod
    def list_agents(self, role: Optional[str] = None, status: Optional[str] = None) -> List[Agent]:
        """List all registered agents, optionally filtered by role or status."""
        pass

    @abstractmethod
    def get_agents_by_capability(self, capability: str) -> List[Agent]:
        """Discover agents matching a required capability or strength."""
        pass
