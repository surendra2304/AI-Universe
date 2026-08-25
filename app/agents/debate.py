"""Real-Time Multi-Agent Collaboration Engine for AI Universe.

Implements the "Collaborate First, Debate on Conflict" model:
- Step 1: Selected specialist agents generate independent perspectives in parallel via asyncio.gather.
- Step 2: The Synthesizer immediately reviews the parallel responses and checks for major contradictions.
- Step 3: If agents agree, the Synthesizer merges them into a final answer INSTANTLY (mode_used = "collaboration" or "consensus").
- Step 4: ONLY IF the Synthesizer detects severe contradictions or unsafe logic, a targeted Rebuttal round is triggered.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.agents.base import Agent, BaseAgentRegistry
from app.agents.registry import agent_registry
from app.memory.base import BaseMemory, MessageRecord, RunRecord
from app.memory.sqlite import SQLiteMemory
from app.core.policies import ProviderSwitchingPolicy, SwitchReason
from app.providers import get_provider
from app.providers.base import ProviderMessage, ProviderRequest
from app.utils.ids import generate_debate_id, generate_message_id, generate_run_id
from app.utils.logger import logger


class CollaborationMessage(BaseModel):
    """An individual message or perspective in a collaborative session."""
    id: str = Field(default_factory=generate_message_id)
    round_number: int
    stage_name: str
    agent_id: str
    agent_role: str
    content: str
    target_agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CollaborationRoundLog(BaseModel):
    """Log record summarizing an individual round in the collaboration."""
    round_number: int
    stage_name: str
    messages: List[CollaborationMessage] = Field(default_factory=list)
    summary: Optional[str] = None


# Backward-compatibility alias for tests and older consumers
DebateRoundLog = CollaborationRoundLog
DebateMessage = CollaborationMessage


class CollaborationResult(BaseModel):
    """Outcome of the Real-Time Multi-Agent Collaboration Engine."""
    debate_id: str
    task_id: str
    canonical_problem: str
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    unresolved_disagreements: List[str] = Field(default_factory=list)
    key_evidence: List[str] = Field(default_factory=list)
    participating_agents: List[str]
    rounds: List[CollaborationRoundLog]
    mode_used: str = "collaboration"
    total_tokens: int = 0
    total_latency_seconds: float = 0.0


# Backward-compatibility alias
DebateResult = CollaborationResult


class CollaborationEngine:
    """Coordinates Real-Time Multi-Agent Collaboration and targeted conflict resolution."""

    def __init__(
        self,
        memory: Optional[BaseMemory] = None,
        registry: Optional[BaseAgentRegistry] = None
    ) -> None:
        self.memory = memory or SQLiteMemory()
        self.registry = registry or agent_registry

    async def _execute_agent_call(
        self,
        task_id: str,
        stage_name: str,
        round_number: int,
        agent: Agent,
        messages: List[ProviderMessage],
        system_override: Optional[str] = None
    ) -> Tuple[str, int, float]:
        """Helper to invoke a single agent, log the run and message to SQLite."""
        run_id = generate_run_id()
        msg_id = generate_message_id()
        provider = get_provider(agent.model_provider)
        start_time = time.perf_counter()

        system_instruction = system_override or agent.system_instructions
        req = ProviderRequest(
            messages=messages,
            system_instruction=system_instruction,
            model=agent.model_name,
            max_tokens=1024
        )

        resp = None
        last_error = None
        for attempt in range(2):
            try:
                resp = await provider.generate(req)
                break
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.3)

        if resp is None:
            fallback_route = ProviderSwitchingPolicy.get_fallback_provider(
                agent.model_provider, SwitchReason.TIMEOUT, stage=stage_name
            )
            if fallback_route:
                try:
                    fallback_prov = get_provider(fallback_route.fallback_provider)
                    fallback_req = ProviderRequest(
                        messages=messages,
                        system_instruction=system_instruction,
                        model=fallback_route.fallback_model,
                        max_tokens=1024
                    )
                    resp = await fallback_prov.generate(fallback_req)
                except Exception as fb_exc:
                    last_error = fb_exc

        if resp is not None:
            latency = time.perf_counter() - start_time
            tokens = resp.total_tokens or 0

            # 1. Save Run Audit
            run_rec = RunRecord(
                id=run_id,
                task_id=task_id,
                agent_id=agent.id,
                provider=resp.provider or provider.provider_name,
                model=resp.model,
                stage=f"round_{round_number}_{stage_name}",
                prompt_tokens=resp.prompt_tokens or 0,
                completion_tokens=resp.completion_tokens or 0,
                latency_seconds=latency,
                status="completed"
            )
            await self.memory.save_run(run_rec)

            # 2. Save Message Record
            msg_rec = MessageRecord(
                id=msg_id,
                run_id=run_id,
                task_id=task_id,
                role="assistant",
                agent_id=agent.id,
                content=resp.content,
                stage=f"round_{round_number}_{stage_name}"
            )
            await self.memory.save_message(msg_rec)

            return resp.content, tokens, latency
        else:
            latency = time.perf_counter() - start_time
            error_msg = str(last_error).split('\n')[0]
            logger.warning("Collaboration call for agent %s in %s had an issue: %s", agent.id, stage_name, error_msg)
            run_rec = RunRecord(
                id=run_id,
                task_id=task_id,
                agent_id=agent.id,
                provider=provider.provider_name,
                model=agent.model_name,
                stage=f"round_{round_number}_{stage_name}",
                latency_seconds=latency,
                status="failed",
                error=error_msg
            )
            await self.memory.save_run(run_rec)
            fallback_content = f"*[Specialist {agent.role} temporarily offline / high demand on {provider.provider_name}: {error_msg}]*"
            return fallback_content, 0, latency

    async def run_collaboration(
        self,
        task_id: str,
        question: str,
        participating_agents: Optional[List[Agent]] = None,
        require_evidence: bool = True
    ) -> CollaborationResult:
        """
        Executes the Real-Time Parallel Collaboration Protocol:
        1. Parallel Specialist Perspectives (Round 1) via asyncio.gather.
        2. Synthesizer Instant Contradiction & Alignment Check.
        3. If aligned: Instant Merged Synthesis (sub-second post-step).
        4. If severe conflict: Targeted Rebuttal round between conflicting specialists.
        """
        session_id = generate_debate_id()
        start_total_time = time.perf_counter()
        total_tokens = 0
        rounds_log: List[CollaborationRoundLog] = []

        if not participating_agents:
            agent_ids = ["architect", "security_analyst", "coder"]
            participating_agents = [self.registry.get_agent(aid) for aid in agent_ids if self.registry.get_agent(aid)]

        synthesizer_agent = self.registry.get_agent("synthesizer") or participating_agents[0]
        critic_agent = self.registry.get_agent("critic") or participating_agents[-1]

        # -------------------------------------------------------------
        # STEP 1: Parallel Independent Analysis (Round 1)
        # -------------------------------------------------------------
        logger.info("Collaboration %s: Firing parallel specialist analysis for %d agents", session_id, len(participating_agents))

        async def analyze_agent(agent: Agent) -> Tuple[Agent, str, int]:
            prompt = (
                f"Question / Goal:\n{question}\n\n"
                f"As the {agent.role}, provide your direct, concise technical recommendation and core rationale. "
                "Be concrete, identify primary trade-offs, and state assumptions explicitly."
            )
            text, t_count, _ = await self._execute_agent_call(
                task_id=task_id,
                stage_name="independent_analysis",
                round_number=1,
                agent=agent,
                messages=[ProviderMessage(role="user", content=prompt)]
            )
            return agent, text, t_count

        # Execute all specialist perspectives simultaneously with asyncio.gather
        r1_results = await asyncio.gather(*[analyze_agent(agent) for agent in participating_agents])
        round_1_messages: List[CollaborationMessage] = []

        for agent, text, t_count in r1_results:
            total_tokens += t_count
            round_1_messages.append(CollaborationMessage(
                round_number=1,
                stage_name="Independent Analysis",
                agent_id=agent.id,
                agent_role=agent.role,
                content=text
            ))

        rounds_log.append(CollaborationRoundLog(
            round_number=1,
            stage_name="Independent Analysis",
            messages=round_1_messages,
            summary=f"Gathered {len(round_1_messages)} parallel specialist perspectives."
        ))

        combined_proposals = "\n\n".join([
            f"=== Specialist Perspective: {m.agent_role} ({m.agent_id}) ===\n{m.content}"
            for m in round_1_messages
        ])

        # -------------------------------------------------------------
        # STEP 2 & 3: Synthesizer Review & Instant Consensus Merge
        # -------------------------------------------------------------
        logger.info("Collaboration %s: Synthesizer reviewing parallel responses for conflict vs consensus", session_id)
        synthesis_prompt = (
            f"User Goal / Question:\n{question}\n\n"
            f"Specialist Proposals:\n{combined_proposals}\n\n"
            "As the Consensus Synthesizer, evaluate the specialist proposals:\n"
            "1. If they are fundamentally aligned, merge them immediately into one comprehensive, unified, "
            "and actionable final answer. Explicitly call out the winning recommendations and key trade-offs.\n"
            "2. If there is an irreconcilable, dangerous technical conflict (e.g. security flaw or incompatible architectures), "
            "start your response with 'CONFLICT_DETECTED:' followed by a description of the exact dispute.\n"
        )

        synthesis_text, syn_tokens, _ = await self._execute_agent_call(
            task_id=task_id,
            stage_name="consensus_synthesis",
            round_number=2,
            agent=synthesizer_agent,
            messages=[ProviderMessage(role="user", content=synthesis_prompt)]
        )
        total_tokens += syn_tokens

        has_severe_conflict = synthesis_text.strip().startswith("CONFLICT_DETECTED:") or (
            "CONSENSUS_REACHED: NO" in synthesis_text.upper()
        )

        # -------------------------------------------------------------
        # STEP 4: Targeted Rebuttal ONLY IF Severe Conflict Exists
        # -------------------------------------------------------------
        if has_severe_conflict:
            logger.warning("Collaboration %s: Severe conflict detected. Triggering targeted adversarial rebuttal.", session_id)
            rebuttal_prompt = (
                f"Question:\n{question}\n\n"
                f"Initial Proposals:\n{combined_proposals}\n\n"
                f"Identified Conflict:\n{synthesis_text}\n\n"
                "As the Adversarial Critic, challenge the conflicting assumptions and propose the safest resolution."
            )
            rebuttal_text, reb_tokens, _ = await self._execute_agent_call(
                task_id=task_id,
                stage_name="targeted_rebuttal",
                round_number=3,
                agent=critic_agent,
                messages=[ProviderMessage(role="user", content=rebuttal_prompt)]
            )
            total_tokens += reb_tokens

            rounds_log.append(CollaborationRoundLog(
                round_number=3,
                stage_name="Targeted Rebuttal",
                messages=[CollaborationMessage(
                    round_number=3,
                    stage_name="Targeted Rebuttal",
                    agent_id=critic_agent.id,
                    agent_role=critic_agent.role,
                    content=rebuttal_text
                )],
                summary="Targeted rebuttal resolved conflicting specialist assumptions."
            ))

            # Final resolution synthesis post-rebuttal
            final_synth_prompt = (
                f"Question:\n{question}\n\n"
                f"Targeted Rebuttal & Critique:\n{rebuttal_text}\n\n"
                "Produce the final, conclusive architectural recommendation resolving the debate."
            )
            final_answer, fin_tokens, _ = await self._execute_agent_call(
                task_id=task_id,
                stage_name="final_resolution",
                round_number=4,
                agent=synthesizer_agent,
                messages=[ProviderMessage(role="user", content=final_synth_prompt)]
            )
            total_tokens += fin_tokens

            rounds_log.append(CollaborationRoundLog(
                round_number=4,
                stage_name="Final Resolution",
                messages=[CollaborationMessage(
                    round_number=4,
                    stage_name="Final Resolution",
                    agent_id=synthesizer_agent.id,
                    agent_role=synthesizer_agent.role,
                    content=final_answer
                )],
                summary="Synthesizer delivered resolved decision after targeted debate."
            ))

            total_duration = time.perf_counter() - start_total_time
            return CollaborationResult(
                debate_id=session_id,
                task_id=task_id,
                canonical_problem=question,
                final_answer=final_answer,
                confidence=0.88,
                unresolved_disagreements=["Addressed through targeted adversarial rebuttal."],
                key_evidence=["Resolved through targeted cross-specialist debate."],
                participating_agents=[a.id for a in participating_agents],
                rounds=rounds_log,
                mode_used="debate",
                total_tokens=total_tokens,
                total_latency_seconds=round(total_duration, 4)
            )

        # Direct Instant Synthesis (Standard fast path)
        rounds_log.append(CollaborationRoundLog(
            round_number=2,
            stage_name="Consensus Synthesis",
            messages=[CollaborationMessage(
                round_number=2,
                stage_name="Consensus Synthesis",
                agent_id=synthesizer_agent.id,
                agent_role=synthesizer_agent.role,
                content=synthesis_text
            )],
            summary="Synthesizer successfully merged aligned specialist perspectives instantly."
        ))

        total_duration = time.perf_counter() - start_total_time
        logger.info("Collaboration %s finished in %.2fs consuming ~%d tokens", session_id, total_duration, total_tokens)

        return CollaborationResult(
            debate_id=session_id,
            task_id=task_id,
            canonical_problem=question,
            final_answer=synthesis_text,
            confidence=0.92,
            unresolved_disagreements=[],
            key_evidence=["High specialist alignment merged into unified consensus."],
            participating_agents=[a.id for a in participating_agents],
            rounds=rounds_log,
            mode_used="consensus",
            total_tokens=total_tokens,
            total_latency_seconds=round(total_duration, 4)
        )

    # Backward-compatibility alias
    async def run_debate(
        self,
        task_id: str,
        question: str,
        participating_agents: Optional[List[Agent]] = None,
        require_evidence: bool = True
    ) -> CollaborationResult:
        """Backward-compatible entry point delegating to run_collaboration."""
        return await self.run_collaboration(
            task_id=task_id,
            question=question,
            participating_agents=participating_agents,
            require_evidence=require_evidence
        )


# Global default instances
collaboration_engine = CollaborationEngine()
DebateEngine = CollaborationEngine
debate_engine = collaboration_engine
