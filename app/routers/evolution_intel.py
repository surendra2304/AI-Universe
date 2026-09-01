"""FastAPI Router for Strategy Evolution Candidates, Overfitting Checks, Regime Tests, and Trends."""

from typing import Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from app.analysis.evolution_trends import evolution_trends_engine
from app.analysis.overfitting_intel import overfitting_engine
from app.analysis.regime_robustness import regime_robustness_engine
from app.debate.strategy_evaluation import strategy_evaluation_debate

evolution_router = APIRouter(prefix="/v1/evolution", tags=["Strategy Evolution Intelligence"])


class StrategyEvaluationRequest(BaseModel):
    strategy_name: str = Field(default="Evolved_ADX_EMA_v4", description="Name of candidate strategy")
    backtest_metrics: dict[str, Any] = Field(
        default={
            "sharpe_ratio": 1.95,
            "profit_factor": 1.72,
            "max_drawdown_pct": 5.8,
            "total_trades": 140
        },
        description="Backtest performance summary"
    )
    regime_metrics: dict[str, Any] | None = Field(
        default=None,
        description="Performance partitioned across Bull, Bear, and Chop regimes"
    )


class OverfittingCheckRequest(BaseModel):
    strategy_name: str = Field(default="Evolved_ADX_EMA_v4")
    backtest_sharpe: float = Field(default=2.1)
    backtest_profit_factor: float = Field(default=1.85)
    total_trades: int = Field(default=120)
    num_trials_tested: int = Field(default=50)


class RegimeTestRequest(BaseModel):
    strategy_name: str = Field(default="Evolved_ADX_EMA_v4")
    regime_metrics: dict[str, dict[str, float]] | None = Field(default=None)


@evolution_router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_strategy_candidate(req: StrategyEvaluationRequest):
    """Conducts full 5-specialist evaluation debate on candidate strategy."""
    return strategy_evaluation_debate.evaluate_strategy_candidate(
        strategy_name=req.strategy_name,
        backtest_metrics=req.backtest_metrics,
        regime_metrics=req.regime_metrics or {}
    )


@evolution_router.post("/overfitting-check", status_code=status.HTTP_200_OK)
async def check_overfitting(req: OverfittingCheckRequest):
    """Calculates Deflated Sharpe Ratio, PBO, and parameter curve-fitting probability."""
    return overfitting_engine.evaluate_strategy_overfitting(
        strategy_name=req.strategy_name,
        backtest_sharpe=req.backtest_sharpe,
        backtest_profit_factor=req.backtest_profit_factor,
        total_trades=req.total_trades,
        num_trials_tested=req.num_trials_tested
    )


@evolution_router.post("/regime-test", status_code=status.HTTP_200_OK)
async def test_strategy_regime_robustness(req: RegimeTestRequest):
    """Tests cross-regime consistency, whipsaw vulnerability, and worst-case drawdown."""
    return regime_robustness_engine.test_regime_robustness(
        strategy_name=req.strategy_name,
        regime_metrics=req.regime_metrics or {}
    )


@evolution_router.get("/trends", status_code=status.HTTP_200_OK)
async def get_evolution_trends(
    generation: int = Query(default=15, description="Current genetic generation"),
    diversity: float = Query(default=0.72, description="Population diversity metric 0.0 - 1.0")
):
    """Returns genetic population health, diversity metrics, and mutation rate recommendations."""
    return evolution_trends_engine.analyze_evolution_trends(
        generation_count=generation,
        diversity_metric=diversity
    )
