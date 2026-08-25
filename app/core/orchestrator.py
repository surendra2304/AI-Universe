"""Orchestrator core module for end-to-end task coordination and execution."""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base import Agent
from app.agents.debate import DebateEngine, debate_engine
from app.agents.registry import agent_registry
from app.agents.roles import register_all_specialists
from app.agents.router import router as task_router
from app.learning.performance import PerformanceTracker
from app.learning.strategy_store import StrategyStore
from app.memory.base import BaseMemory, TaskRecord
from app.memory.sqlite import SQLiteMemory
from app.utils.ids import generate_task_id
from app.utils.logger import logger


class OrchestrationRequest(BaseModel):
    """Input payload for a high-level orchestration task."""
    question: str
    mode: str = Field(default="auto", description="auto, fast, review, debate")
    max_agents: int = Field(default=5, ge=1, le=10)
    require_evidence: bool = True
    max_budget: Optional[float] = Field(default=None, description="Max budget in USD for this task")
    max_latency: Optional[float] = Field(default=None, description="Max desired latency in seconds")
    context_data: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationResult(BaseModel):
    """Final result output from an orchestrated workflow."""
    task_id: str
    run_id: str
    question: str
    answer: str
    mode_used: str
    provider_used: str = "gemini"
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
        self.debate_engine = DebateEngine(memory=self.memory, registry=self.registry)
        self.strategy_store = StrategyStore(memory=self.memory)
        self.performance_tracker = PerformanceTracker(memory=self.memory)
        
        # Ensure all 10 specialist roles are registered
        register_all_specialists()

    async def process_task(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Execute full end-to-end question answering vertical slice."""
        task_id = generate_task_id()
        start_time = time.perf_counter()

        self.strategy_store.memory = self.memory
        self.performance_tracker.memory = self.memory
        self.debate_engine.memory = self.memory

        # Check for learned strategy recommendations if mode is 'auto'
        learned_strat = None
        if request.mode == "auto":
            task_domain = self.router.detect_domain_specialist(request.question)
            try:
                learned_strat = await self.strategy_store.recommend_strategy(task_domain)
            except Exception as e:
                logger.debug("Strategy store lookup skipped: %s", str(e))

        # 1. Route task and select specialist agents with telemetry guardrails
        decision = self.router.route_task(
            question=request.question,
            requested_mode=learned_strat.recommended_mode if learned_strat else request.mode,
            max_agents=request.max_agents,
            max_budget=request.max_budget,
            max_latency=request.max_latency
        )

        mode_used = decision.mode
        route_reason = decision.reason
        selected_agent_ids = decision.selected_agent_ids
        participating_agents = [
            self.registry.get_agent(aid) for aid in selected_agent_ids
            if self.registry.get_agent(aid)
        ]

        # 2. Create initial task record in SQLite with telemetry metadata
        task_record = TaskRecord(
            id=task_id,
            question=request.question,
            mode=mode_used,
            status="running",
            metadata={
                "route_reason": route_reason,
                "selected_agents": selected_agent_ids,
                "routing_telemetry": decision.telemetry,
                "learned_strategy_applied": bool(learned_strat),
                "request_context": request.context_data
            }
        )
        await self.memory.save_task(task_record)

        try:
            # ALL MODES use the CollaborationEngine for parallel teamwork:
            # fast   → 2 agents in parallel (primary domain specialist + Synthesizer)
            # review → 3 agents in parallel (router pair + one cross-checker)
            # debate → full router panel (3-5 agents)
            # CollaborationEngine handles instant consensus merge OR targeted rebuttal internally.

            if mode_used == "fast" and len(participating_agents) < 2:
                # Pad to 2 agents: add Synthesizer as the second collaborator
                synthesizer = self.registry.get_agent("synthesizer")
                if synthesizer and (not participating_agents or synthesizer.id != participating_agents[0].id):
                    participating_agents = participating_agents + [synthesizer]

            elif mode_used == "review" and len(participating_agents) < 3:
                # Pad to 3 agents: add a cross-checking specialist
                extra_candidates = ["fact_checker", "critic", "strategist", "researcher"]
                existing_ids = [a.id for a in participating_agents]
                for cid in extra_candidates:
                    if len(participating_agents) >= 3:
                        break
                    agent = self.registry.get_agent(cid)
                    if agent and agent.id not in existing_ids:
                        participating_agents = participating_agents + [agent]
                        existing_ids.append(agent.id)

            logger.info(
                "CollaborationEngine: task %s | mode '%s' | %d agents: %s",
                task_id, mode_used, len(participating_agents),
                [a.id for a in participating_agents]
            )

            self.debate_engine.memory = self.memory
            collab_result = await self.debate_engine.run_collaboration(
                task_id=task_id,
                question=request.question,
                participating_agents=participating_agents,
                require_evidence=request.require_evidence
            )
            latency = time.perf_counter() - start_time

            actual_mode = getattr(collab_result, "mode_used", mode_used)
            task_record.status = "completed"
            task_record.result = collab_result.final_answer
            task_record.confidence = collab_result.confidence
            task_record.mode = actual_mode
            task_record.completed_at = datetime.utcnow()
            task_record.metadata["debate_id"] = collab_result.debate_id
            task_record.metadata["unresolved_disagreements"] = collab_result.unresolved_disagreements
            await self.memory.save_task(task_record)

            return OrchestrationResult(
                task_id=task_id,
                run_id=collab_result.debate_id,
                question=request.question,
                answer=collab_result.final_answer,
                mode_used=actual_mode,
                provider_used="multi_provider",
                agents_used=collab_result.participating_agents,
                models_used=[a.model_name for a in participating_agents],
                confidence=collab_result.confidence,
                unresolved_disagreements=collab_result.unresolved_disagreements,
                key_evidence=collab_result.key_evidence,
                total_tokens=collab_result.total_tokens,
                total_latency_seconds=round(latency, 4)
            )

        except Exception as exc:
            latency = time.perf_counter() - start_time
            logger.error("Task %s failed during execution: %s", task_id, str(exc))

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
