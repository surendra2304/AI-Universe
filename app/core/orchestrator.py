"""Orchestrator core module for end-to-end task coordination and execution."""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base import Agent
from app.agents.registry import agent_registry
from app.agents.roles import register_all_specialists
from app.agents.router import router as task_router
from app.memory.base import BaseMemory, RunRecord, TaskRecord
from app.memory.sqlite import SQLiteMemory
from app.providers import get_provider
from app.providers.base import ProviderMessage, ProviderRequest
from app.utils.ids import generate_run_id, generate_task_id
from app.utils.logger import logger


class OrchestrationRequest(BaseModel):
    """Input payload for a high-level orchestration task."""
    question: str
    mode: str = Field(default="auto", description="auto, fast, review, debate")
    max_agents: int = Field(default=5, ge=1, le=10)
    require_evidence: bool = True
    context_data: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationResult(BaseModel):
    """Final result output from an orchestrated workflow."""
    task_id: str
    run_id: str
    question: str
    answer: str
    mode_used: str
    agents_used: List[str]
    models_used: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    unresolved_disagreements: List[str] = Field(default_factory=list)
    key_evidence: List[str] = Field(default_factory=list)
    total_tokens: int = 0
    total_latency_seconds: float = 0.0


class BaseOrchestrator(ABC):
    """Abstract base class for coordinating tasks from start to finish."""

    @abstractmethod
    async def process_task(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Execute full end-to-end task routing, reasoning/debate, and answer synthesis."""
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an in-flight orchestration task."""
        pass

    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve live execution progress and state of an ongoing or completed task."""
        pass


class Orchestrator(BaseOrchestrator):
    """Coordinates task routing, agent assignment, execution, memory persistence, and synthesis."""

    def __init__(
        self,
        memory: Optional[BaseMemory] = None,
    ) -> None:
        self.memory = memory or SQLiteMemory()
        self.router = task_router
        self.registry = agent_registry
        
        # Ensure all 10 specialist roles are registered
        register_all_specialists()

    async def process_task(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Execute full end-to-end question answering vertical slice."""
        task_id = generate_task_id()
        run_id = generate_run_id()
        start_time = time.perf_counter()

        # 1. Route task and select specialist agents
        decision = self.router.route_task(
            question=request.question,
            requested_mode=request.mode,
            max_agents=request.max_agents
        )

        mode_used = decision.mode
        route_reason = decision.reason
        selected_agent_ids = decision.selected_agent_ids
        primary_agent_id = selected_agent_ids[0]

        # 2. Retrieve primary agent configuration from registry
        agent = self.registry.get_agent(primary_agent_id) or self.registry.get_agent("researcher")
        provider = get_provider(agent.model_provider)

        # 3. Create and persist initial task record
        task_record = TaskRecord(
            id=task_id,
            question=request.question,
            mode=mode_used,
            status="running",
            metadata={
                "route_reason": route_reason,
                "selected_agents": selected_agent_ids,
                "primary_agent": agent.id,
                "request_context": request.context_data
            }
        )
        await self.memory.save_task(task_record)

        # 4. Retrieve agent memories if available
        prior_memories = await self.memory.get_agent_memories(agent.id, limit=3)
        memory_context = "\n".join([f"- {m.content}" for m in prior_memories]) if prior_memories else ""

        system_prompt = agent.system_instructions
        if memory_context:
            system_prompt += f"\n\nContext & Relevant Past Memory:\n{memory_context}"

        # 5. Dispatch request to provider
        provider_req = ProviderRequest(
            messages=[ProviderMessage(role="user", content=request.question)],
            system_instruction=system_prompt,
            model=agent.model_name
        )

        try:
            response = await provider.generate(provider_req)
            latency = time.perf_counter() - start_time

            # 6. Persist Run record audit trail
            run_record = RunRecord(
                id=run_id,
                task_id=task_id,
                agent_id=agent.id,
                provider=provider.provider_name,
                model=response.model,
                stage=f"{mode_used}_execution",
                prompt_tokens=response.prompt_tokens or 0,
                completion_tokens=response.completion_tokens or 0,
                latency_seconds=latency,
                status="completed"
            )
            await self.memory.save_run(run_record)

            # 7. Update Task record with completion state
            task_record.status = "completed"
            task_record.result = response.content
            task_record.confidence = 0.90
            task_record.completed_at = datetime.utcnow()
            await self.memory.save_task(task_record)

            return OrchestrationResult(
                task_id=task_id,
                run_id=run_id,
                question=request.question,
                answer=response.content,
                mode_used=mode_used,
                agents_used=selected_agent_ids,
                models_used=[response.model],
                confidence=0.90,
                total_tokens=response.total_tokens or 0,
                total_latency_seconds=round(latency, 4)
            )

        except Exception as exc:
            latency = time.perf_counter() - start_time
            logger.error("Task %s failed during execution: %s", task_id, str(exc))

            run_record = RunRecord(
                id=run_id,
                task_id=task_id,
                agent_id=agent.id,
                provider=provider.provider_name,
                model=agent.model_name,
                stage=f"{mode_used}_execution",
                latency_seconds=latency,
                status="failed",
                error=str(exc)
            )
            await self.memory.save_run(run_record)

            task_record.status = "failed"
            task_record.completed_at = datetime.utcnow()
            task_record.metadata["error"] = str(exc)
            await self.memory.save_task(task_record)

            raise exc

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an in-flight task."""
        task = await self.memory.get_task(task_id)
        if task and task.status == "running":
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()
            await self.memory.save_task(task)
            return True
        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task details and progress."""
        task = await self.memory.get_task(task_id)
        return task.model_dump() if task else None


# Global default orchestrator instance
orchestrator = Orchestrator()
