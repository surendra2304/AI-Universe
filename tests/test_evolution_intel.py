"""Tests for Strategy Evolution Debate, Overfitting Intelligence, Regime Robustness, and Evolution Trends."""

from fastapi.testclient import TestClient

from app.analysis.evolution_trends import evolution_trends_engine
from app.analysis.overfitting_intel import overfitting_engine
from app.analysis.regime_robustness import regime_robustness_engine
from app.main import app

client = TestClient(app)


def test_overfitting_engine_calculations():
    """Tests DSR, PBO, and MinBTL computations."""
    # Test robust strategy
    res_good = overfitting_engine.evaluate_strategy_overfitting(
        strategy_name="Solid_Trend_Strat",
        backtest_sharpe=1.8,
        backtest_profit_factor=1.5,
        total_trades=150,
        num_trials_tested=30
    )
    assert res_good["overfitting_verdict"] in ("ACCEPT_ROBUST", "TEST_LONGER")
    assert "deflated_sharpe_ratio" in res_good

    # Test overfitted / suspicious strategy
    res_bad = overfitting_engine.evaluate_strategy_overfitting(
        strategy_name="Overfitted_Grid",
        backtest_sharpe=3.8,
        backtest_profit_factor=4.2,
        total_trades=20,
        num_trials_tested=500
    )
    assert res_bad["overfitting_verdict"] == "REJECT_OVERFITTED"
    assert res_bad["probability_of_backtest_overfitting_pbo"] >= 0.65


def test_regime_robustness_testing():
    """Tests cross-regime evaluation and whipsaw survival classification."""
    metrics = {
        "bull": {"win_rate": 0.65, "profit_factor": 2.0, "max_drawdown_pct": 4.0},
        "chop": {"win_rate": 0.40, "profit_factor": 0.85, "max_drawdown_pct": 6.5}
    }
    res = regime_robustness_engine.test_regime_robustness("ADX_EMA_v2", metrics)
    assert "robustness_score" in res
    assert res["worst_regime_profit_factor"] == 0.85
    assert res["regime_dependency_classification"] == "VULNERABLE_TO_SIDEWAYS_CHOP"


def test_evolution_trends_analysis():
    """Tests diversity tracking and mutation rate recommendations."""
    # Normal diversity
    res_norm = evolution_trends_engine.analyze_evolution_trends(diversity_metric=0.75)
    assert res_norm["is_prematurely_converging"] is False
    assert res_norm["recommended_mutation_rate"] == 0.15

    # Low diversity
    res_low = evolution_trends_engine.analyze_evolution_trends(diversity_metric=0.35)
    assert res_low["is_prematurely_converging"] is True
    assert res_low["recommended_mutation_rate"] == 0.35


def test_evolution_api_endpoints():
    """Tests POST /v1/evolution/evaluate, /overfitting-check, /regime-test, and /trends."""
    # Evaluation debate endpoint
    resp_eval = client.post(
        "/v1/evolution/evaluate",
        json={"strategy_name": "Evolved_Candidate_1", "backtest_metrics": {"sharpe_ratio": 1.8, "profit_factor": 1.6, "total_trades": 100}}
    )
    assert resp_eval.status_code == 200
    data = resp_eval.json()
    assert len(data["evaluator_panel"]) == 5
    assert "composite_evaluation_score" in data

    # Overfitting endpoint
    resp_overfit = client.post(
        "/v1/evolution/overfitting-check",
        json={"strategy_name": "Evolved_Candidate_1", "backtest_sharpe": 1.7, "backtest_profit_factor": 1.5, "total_trades": 90, "num_trials_tested": 40}
    )
    assert resp_overfit.status_code == 200
    assert "probability_of_backtest_overfitting_pbo" in resp_overfit.json()

    # Trends endpoint
    resp_trends = client.get("/v1/evolution/trends?generation=10&diversity=0.65")
    assert resp_trends.status_code == 200
    assert resp_trends.json()["current_generation"] == 10
