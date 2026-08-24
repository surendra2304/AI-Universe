"""Base interface and data contracts for persistent memory storage."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """An individual persistent memory record scoped to an agent or system."""
    id: str
    agent_id: str
    content: str
    memory_type: str = Field(default="fact", description="fact, experience, preference, decision, reflection")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    context_tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskRecord(BaseModel):
    """Audit record for a submitted user/system task."""
    id: str
    question: str
    mode: str = Field(default="auto", description="auto, fast, review, debate")
    status: str = Field(default="pending", description="pending, running, completed, failed")
    result: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    """Audit record for a specific reasoning stage or agent invocation."""
    id: str
    task_id: str
    agent_id: str
    provider: str
    model: str
    stage: str = Field(description="round_0_framing, round_1_analysis, round_2_critique, etc.")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    status: str = "completed"
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MessageRecord(BaseModel):
    """Record for conversation or debate messages."""
    id: str
    run_id: str
    task_id: str
    role: str
    agent_id: Optional[str] = None
    content: str
    stage: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BaseMemory(ABC):
    """Abstract base class for persistent memory operations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize database schema, tables, and indexes."""
        pass

    @abstractmethod
    async def save_agent(self, agent_data: Dict[str, Any]) -> None:
        """Persist or update an agent configuration record."""
        pass

    @abstractmethod
    async def save_task(self, task: TaskRecord) -> None:
        """Create or update a task record."""
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Retrieve a task record by its ID."""
        pass

    @abstractmethod
    async def save_run(self, run: RunRecord) -> None:
        """Persist an execution run audit record."""
        pass

    @abstractmethod
    async def save_message(self, message: MessageRecord) -> None:
        """Persist a conversation or debate message."""
        pass

    @abstractmethod
    async def get_task_messages(self, task_id: str) -> List[MessageRecord]:
        """Retrieve all messages associated with a task ID."""
        pass

    @abstractmethod
    async def save_memory(self, memory: MemoryRecord) -> None:
        """Save a scoped persistent memory item."""
        pass

    @abstractmethod
    async def get_agent_memories(
        self,
        agent_id: str,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[MemoryRecord]:
        """Retrieve memories strictly scoped to a specific agent_id."""
        pass

    @abstractmethod
    async def search_memories(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 5
    ) -> List[MemoryRecord]:
        """Search memory records by semantic/text query, optionally filtered by agent_id."""
        pass
