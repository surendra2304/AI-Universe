"""Evaluator base interface and data models for scoring outcomes."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
