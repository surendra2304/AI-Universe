"""Tests for Live Capital Intelligence, Crisis Protocols, Stress Tests, and Conservative Engine."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.conservative_engine import conservative_engine
from app.services.crisis_detector import CrisisLevel, crisis_detector
from app.services.live_consult_profile import live_consult_profile

client = TestClient(app)


def test_live_consult_profile_constraints_and_veto():
    """Tests that live profile constrains changes and applies critic veto."""
    # Test critic veto
    res = live_consult_profile.apply_live_profile_constraints(
        decision_type="OPTIMIZE_PARAMETERS",
        confidence=0.88,
        proposed_changes={"take_profit_multiplier": 1.05},
        critic_opposition_score=0.85,
        total_trades=60
    )
    assert res["decision_type"] == "OBSERVATION_ONLY"
    assert res["critic_veto_exercised"] is True

    # Test trade count insufficiency
    res_trades = live_consult_profile.apply_live_profile_constraints(
        decision_type="OPTIMIZE_PARAMETERS",
        confidence=0.88,
        proposed_changes={"take_profit_multiplier": 1.05},
        critic_opposition_score=0.20,
        total_trades=25
    )
    assert res_trades["decision_type"] == "OBSERVATION_ONLY"


def test_crisis_detector_levels():
    """Tests multi-tier crisis detection logic."""
    normal = crisis_detector.evaluate_crisis_level(current_drawdown_pct=2.0, consecutive_losses=1)
    assert normal["crisis_level"] == CrisisLevel.LEVEL_0_NORMAL.value
    assert normal["is_defense_only_mode"] is False

    watch = crisis_detector.evaluate_crisis_level(current_drawdown_pct=4.5, consecutive_losses=3)
    assert watch["crisis_level"] == CrisisLevel.LEVEL_1_WATCH.value

    alert = crisis_detector.evaluate_crisis_level(current_drawdown_pct=8.0, consecutive_losses=5)
    assert alert["crisis_level"] == CrisisLevel.LEVEL_2_ALERT.value
    assert alert["is_defense_only_mode"] is True

    crisis = crisis_detector.evaluate_crisis_level(current_drawdown_pct=13.5, consecutive_losses=8)
    assert crisis["crisis_level"] == CrisisLevel.LEVEL_3_CRISIS.value
    assert "HALT_NEW_ENTRIES" in crisis["recommended_defensive_actions"]


def test_conservative_engine_hierarchy():
    """Tests that conservative engine defaults to risk reduction during drawdown."""
    # Drawdown elevated -> REDUCE_RISK
    rec_risk = conservative_engine.generate_conservative_recommendation(
        strategy_name="Trend_Strat",
        current_drawdown_pct=6.5,
        profit_factor=0.9,
        confidence=0.85
    )
    assert rec_risk["recommended_action"] == "REDUCE_RISK"
    assert "what_could_go_wrong" in rec_risk

    # Modest confidence -> NO_CHANGE
    rec_hold = conservative_engine.generate_conservative_recommendation(
        strategy_name="Trend_Strat",
        current_drawdown_pct=1.5,
        profit_factor=1.6,
        confidence=0.72
    )
    assert rec_hold["recommended_action"] == "NO_CHANGE"


def test_live_intelligence_endpoints():
    """Tests GET /v1/trading/live/intelligence and crisis/stress endpoints."""
    resp = client.get("/v1/trading/live/intelligence?drawdown_pct=3.0&consecutive_losses=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["trading_mode"] == "LIVE"
    assert "crisis_evaluation" in data
    assert "market_stress" in data

    # Crisis status endpoint
    resp_crisis = client.get("/v1/trading/live/crisis-status?drawdown_pct=14.0&consecutive_losses=7")
    assert resp_crisis.status_code == 200
    assert resp_crisis.json()["crisis_level"] == "CRISIS"

    # Stress test endpoint
    resp_stress = client.post("/v1/trading/live/stress-test", json={"portfolio_equity": 10000.0, "active_notional": 3000.0})
    assert resp_stress.status_code == 200
    assert len(resp_stress.json()["scenario_results"]) == 3

    # Live attribution endpoint
    resp_attr = client.get("/v1/trading/live/attribution")
    assert resp_attr.status_code == 200
    assert "strategy_reliability_score" in resp_attr.json()
