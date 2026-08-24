"""Unit tests for the Evaluator, rubrics, and Golden Benchmark dataset."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.evaluation.benchmarks import GOLDEN_BENCHMARK_SUITE, get_benchmark_by_id
from app.evaluation.evaluator import Evaluator, evaluator
from app.evaluation.rubrics import EVALUATION_RUBRICS, RUBRIC_DIMENSION_NAMES
from app.providers.base import ProviderResponse


def test_rubrics_completeness():
    assert len(RUBRIC_DIMENSION_NAMES) == 8
    expected_dims = [
        "correctness", "relevance", "completeness", "reasoning_quality",
        "evidence_quality", "safety", "latency", "usage_efficiency"
    ]
    for d in expected_dims:
        assert d in EVALUATION_RUBRICS
        assert len(EVALUATION_RUBRICS[d].description) > 10
        assert len(EVALUATION_RUBRICS[d].high_score_criteria) > 10


def test_golden_benchmark_dataset():
    assert len(GOLDEN_BENCHMARK_SUITE) >= 5
    domains = [b.domain for b in GOLDEN_BENCHMARK_SUITE]
    assert "architecture" in domains
    assert "coding" in domains
    assert "debugging" in domains
    assert "security" in domains
    assert "reasoning" in domains

    arch_bench = get_benchmark_by_id("bench_001_arch")
    assert arch_bench is not None
    assert len(arch_bench.expected_key_concepts) > 0
    assert len(arch_bench.required_dissent_or_tradeoffs) > 0


@pytest.mark.asyncio
async def test_evaluator_scoring_with_mock_judge():
    mock_judge_payload = {
        "scores": [
            {"criterion": "correctness", "score": 0.95, "reasoning": "Accurate technical specifications."},
            {"criterion": "relevance", "score": 1.0, "reasoning": "Directly answered prompt."},
            {"criterion": "completeness", "score": 0.90, "reasoning": "Addressed all edge cases."},
            {"criterion": "reasoning_quality", "score": 0.92, "reasoning": "Rigorously deduced."},
            {"criterion": "evidence_quality", "score": 0.88, "reasoning": "Strong empirical basis."},
            {"criterion": "safety", "score": 1.0, "reasoning": "No security risks detected."}
        ],
        "strengths": ["Clear modular layout", "Explicit failovers"],
        "flaws_identified": ["Minor formatting density"],
        "calibrated_confidence": 0.92
    }

    mock_resp = ProviderResponse(
        content=json.dumps(mock_judge_payload),
        model="gemini-2.5-pro",
        provider="gemini"
    )

    with patch("app.providers.gemini.GeminiProvider.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp

        eval_engine = Evaluator(judge_provider_name="gemini", judge_model_name="gemini-2.5-pro")
        report = await eval_engine.evaluate_answer(
            question="What architecture should I use for a local-first multi-agent system?",
            answer="Use a modular architecture with SQLite persistence and cloud provider gateway.",
            context={
                "latency_seconds": 1.8,
                "total_tokens": 1200,
                "mode_used": "debate",
                "run_id": "run_eval_test_01"
            }
        )

        assert report.run_id == "run_eval_test_01"
        assert len(report.scores) == 8  # 6 LLM dimensions + 2 deterministic dimensions (latency, usage)
        assert report.overall_score >= 0.85
        assert report.confidence == 0.92
        assert "latency" in [s.criterion for s in report.scores]
        assert "usage_efficiency" in [s.criterion for s in report.scores]


@pytest.mark.asyncio
async def test_evaluator_deterministic_bounds():
    eval_engine = Evaluator()
    scores = eval_engine._score_deterministic_dimensions(latency_seconds=0.8, total_tokens=400, mode="fast")
    lat_score = next(s for s in scores if s.criterion == "latency")
    eff_score = next(s for s in scores if s.criterion == "usage_efficiency")
    assert lat_score.score == 1.0
    assert eff_score.score == 1.0
