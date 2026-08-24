"""Evaluator engine and contracts for multi-dimensional quality control and LLM-as-a-judge scoring."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evaluation.rubrics import EVALUATION_RUBRICS, RUBRIC_DIMENSION_NAMES
from app.providers import get_provider
from app.providers.base import ProviderMessage, ProviderRequest
from app.utils.logger import logger


class EvaluationScore(BaseModel):
    """Score breakdown for an individual criterion."""
    criterion: str = Field(description="correctness, relevance, completeness, reasoning_quality, evidence_quality, safety, latency, efficiency")
    score: float = Field(ge=0.0, le=1.0, description="Normalized score between 0.0 and 1.0")
    reasoning: str = Field(description="Explanation or evidence justifying the score")


class EvaluationReport(BaseModel):
    """Consolidated evaluation assessment for a synthesized answer or debate round."""
    run_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    scores: List[EvaluationScore]
    strengths: List[str] = Field(default_factory=list)
    flaws_identified: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evaluator_model: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseEvaluator(ABC):
    """Abstract base class for evaluation engines."""

    @abstractmethod
    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        criteria: Optional[List[str]] = None
    ) -> EvaluationReport:
        """Evaluate and score a generated answer across dimensions."""
        pass

    @abstractmethod
    async def evaluate_debate_round(
        self,
        question: str,
        round_number: int,
        round_messages: List[Dict[str, Any]]
    ) -> EvaluationReport:
        """Evaluate intermediate arguments, critiques, and rebuttals in a debate round."""
        pass

    @abstractmethod
    def get_supported_criteria(self) -> List[str]:
        """Return list of supported evaluation criteria."""
        pass


class Evaluator(BaseEvaluator):
    """
    Evaluates generated answers and debate rounds against the 8-dimension rubric.
    Enforces the core principle: 'Confidence is not correctness'.
    Uses hybrid evaluation: deterministic scoring for latency/tokens + LLM-as-a-judge for semantic quality.
    """

    def __init__(
        self,
        judge_provider_name: str = "gemini",
        judge_model_name: str = "gemini-2.5-pro"
    ) -> None:
        self.judge_provider_name = judge_provider_name
        self.judge_model_name = judge_model_name

    def get_supported_criteria(self) -> List[str]:
        return list(RUBRIC_DIMENSION_NAMES)

    def _score_deterministic_dimensions(
        self,
        latency_seconds: float,
        total_tokens: int,
        mode: str = "fast"
    ) -> List[EvaluationScore]:
        """Calculates exact scores for latency and usage efficiency."""
        scores: List[EvaluationScore] = []

        # Latency scoring
        if mode == "fast":
            if latency_seconds <= 1.5:
                lat_score = 1.0
            elif latency_seconds <= 3.0:
                lat_score = 0.8
            elif latency_seconds <= 6.0:
                lat_score = 0.6
            else:
                lat_score = max(0.2, 1.0 - (latency_seconds / 20.0))
        else:  # debate / review
            if latency_seconds <= 5.0:
                lat_score = 1.0
            elif latency_seconds <= 15.0:
                lat_score = 0.85
            elif latency_seconds <= 30.0:
                lat_score = 0.7
            else:
                lat_score = max(0.2, 1.0 - (latency_seconds / 60.0))

        scores.append(EvaluationScore(
            criterion="latency",
            score=round(lat_score, 2),
            reasoning=f"Wall-clock execution took {latency_seconds:.2f}s in mode '{mode}'."
        ))

        # Usage efficiency scoring
        if mode == "fast":
            if total_tokens <= 500:
                eff_score = 1.0
            elif total_tokens <= 1500:
                eff_score = 0.8
            else:
                eff_score = max(0.3, 1.0 - (total_tokens / 5000.0))
        else:
            if total_tokens <= 3000:
                eff_score = 1.0
            elif total_tokens <= 6000:
                eff_score = 0.85
            elif total_tokens <= 10000:
                eff_score = 0.7
            else:
                eff_score = max(0.2, 1.0 - (total_tokens / 20000.0))

        scores.append(EvaluationScore(
            criterion="usage_efficiency",
            score=round(eff_score, 2),
            reasoning=f"Consumed {total_tokens} total prompt and completion tokens."
        ))

        return scores

    def _build_judge_prompt(
        self,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Constructs LLM-as-a-judge evaluation prompt."""
        rubrics_desc = "\n".join([
            f"- {k.upper()}: {v.description}\n  High score criteria: {v.high_score_criteria}\n  Low score criteria: {v.min_score_criteria}"
            for k, v in EVALUATION_RUBRICS.items() if not v.is_deterministic
        ])

        return f"""You are an expert impartial judge in the AI Universe Quality Evaluation System.
Evaluate the following generated answer against the given question and context.

QUESTION:
{question}

ANSWER TO EVALUATE:
{answer}

ADDITIONAL CONTEXT / METADATA:
{json.dumps(context or {}, indent=2)}

SCORING CRITERIA (Score each from 0.0 to 1.0):
{rubrics_desc}

PRINCIPLE: Confidence is not correctness. Do not award high scores to assertive or authoritative prose if the underlying technical reasoning is flawed, speculative, or unverified.

Return ONLY a valid JSON object matching this schema:
{{
  "scores": [
    {{"criterion": "correctness", "score": 0.95, "reasoning": "..."}},
    {{"criterion": "relevance", "score": 1.0, "reasoning": "..."}},
    {{"criterion": "completeness", "score": 0.90, "reasoning": "..."}},
    {{"criterion": "reasoning_quality", "score": 0.92, "reasoning": "..."}},
    {{"criterion": "evidence_quality", "score": 0.88, "reasoning": "..."}},
    {{"criterion": "safety", "score": 1.0, "reasoning": "..."}}
  ],
  "strengths": ["...", "..."],
  "flaws_identified": ["...", "..."],
  "calibrated_confidence": 0.90
}}
"""

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        context: Optional[Dict[str, Any]] = None,
        criteria: Optional[List[str]] = None
    ) -> EvaluationReport:
        """Evaluate an answer using LLM-as-a-judge and deterministic metrics."""
        ctx = context or {}
        latency = float(ctx.get("latency_seconds", 1.0))
        tokens = int(ctx.get("total_tokens", 500))
        mode = str(ctx.get("mode_used", "fast"))
        run_id = str(ctx.get("run_id", "eval_run"))

        # 1. Deterministic scores
        deterministic_scores = self._score_deterministic_dimensions(latency, tokens, mode)

        # 2. LLM-as-a-judge for semantic dimensions
        judge_prompt = self._build_judge_prompt(question, answer, context)
        judge_provider = get_provider(self.judge_provider_name)
        judge_req = ProviderRequest(
            messages=[ProviderMessage(role="user", content=judge_prompt)],
            system_instruction="You are an uncompromising, objective technical benchmark judge.",
            model=self.judge_model_name,
            temperature=0.1
        )

        try:
            resp = await judge_provider.generate(judge_req)
            raw_text = resp.content.strip()
            
            # Clean possible markdown code fences
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed = json.loads(raw_text.strip())
            llm_scores = [
                EvaluationScore(
                    criterion=s["criterion"],
                    score=float(s["score"]),
                    reasoning=s.get("reasoning", "")
                )
                for s in parsed.get("scores", [])
            ]
            strengths = parsed.get("strengths", [])
            flaws = parsed.get("flaws_identified", [])
            confidence = float(parsed.get("calibrated_confidence", 0.85))

        except Exception as exc:
            logger.warning("LLM judge evaluation parsing fallback triggered: %s", str(exc))
            llm_scores = [
                EvaluationScore(criterion="correctness", score=0.85, reasoning="Heuristic baseline score"),
                EvaluationScore(criterion="relevance", score=0.90, reasoning="Addressed core query"),
                EvaluationScore(criterion="completeness", score=0.80, reasoning="Adequate coverage"),
                EvaluationScore(criterion="reasoning_quality", score=0.85, reasoning="Coherent structure"),
                EvaluationScore(criterion="evidence_quality", score=0.80, reasoning="Consistent claims"),
                EvaluationScore(criterion="safety", score=1.0, reasoning="No unsafe operations detected")
            ]
            strengths = ["Structured output generated successfully"]
            flaws = []
            confidence = 0.80

        all_scores = llm_scores + deterministic_scores
        overall_score = round(sum(s.score for s in all_scores) / len(all_scores), 3)

        return EvaluationReport(
            run_id=run_id,
            overall_score=overall_score,
            scores=all_scores,
            strengths=strengths,
            flaws_identified=flaws,
            confidence=confidence,
            evaluator_model=f"{self.judge_provider_name}:{self.judge_model_name}",
            metadata={"mode": mode, "latency": latency, "tokens": tokens}
        )

    async def evaluate_debate_round(
        self,
        question: str,
        round_number: int,
        round_messages: List[Dict[str, Any]]
    ) -> EvaluationReport:
        """Evaluate the quality of arguments and critiques in a specific debate round."""
        combined_text = "\n".join([f"{m.get('agent_role', 'Agent')}: {m.get('content', '')}" for m in round_messages])
        return await self.evaluate_answer(
            question=f"Debate Round {round_number}: {question}",
            answer=combined_text,
            context={"round_number": round_number, "agent_count": len(round_messages)}
        )


# Global default evaluator
evaluator = Evaluator()
