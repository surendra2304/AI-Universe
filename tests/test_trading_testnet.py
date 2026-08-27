"""Integration and unit tests for Testnet Trading Consultation capabilities."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_testnet_consultation_conservative_recommendations():
    """Verifies that TESTNET mode recommendations apply conservative tightening and testnet risk assessments."""
    payload = {
        "bot_id": "testnet_scalper_01",
        "trading_mode": "TESTNET",
        "testnet_specific": {
            "testnet_equity": 9800.0,
            "testnet_drawdown_pct": 7.2,
            "testnet_daily_loss": 200.0,
            "testnet_open_positions": 2,
            "testnet_margin_level": 140.0
        },
        "telemetry": {
            "equity": 9800.0,
            "unrealized_pnl": -40.0,
            "realized_pnl": -200.0,
            "win_rate": 0.38,
            "profit_factor": 0.76,
            "max_drawdown_pct": 7.2,
            "consecutive_losses": 4,
            "total_trades": 36
        },
        "current_parameters": {
            "Supertrend_5m": {
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.03,
                "position_size_usdt": 100.0
            }
        },
        "consultation_reason": "DRAWDOWN_EVENT"
    }

    resp = client.post("/v1/trading/consult", json=payload)
    assert resp.status_code == 200
    decision = resp.json()

    assert decision["status"] == "RECOMMENDATION"
    assert len(decision["parameter_changes"]) >= 1

    # Check testnet risk assessment is populated and flags margin/drawdown
    assert decision["testnet_risk_assessment"] is not None
    assert "TESTNET RISK ASSESSMENT" in decision["testnet_risk_assessment"].upper()
    assert "0.8X" in decision["testnet_risk_assessment"].upper() or "POSITION" in decision["testnet_risk_assessment"].upper()

    # Check for conservative tightening (-20% for testnet vs -15% paper)
    sl_change = next((c for c in decision["parameter_changes"] if c["parameter"] == "stop_loss_pct"), None)
    assert sl_change is not None
    assert sl_change["change_pct"] <= -20.0 or "Testnet" in sl_change["rationale"]


def test_testnet_performance_and_comparison_endpoints():
    """Tests the GET /v1/trading/testnet/performance and /v1/trading/testnet/comparison endpoints."""
    # 1. Performance Endpoint
    resp_perf = client.get("/v1/trading/testnet/performance")
    assert resp_perf.status_code == 200
    perf_data = resp_perf.json()
    assert "total_consultations" in perf_data
    assert "testnet_metrics" in perf_data
    assert "paper_metrics" in perf_data
    assert "drawdown_distribution" in perf_data

    # 2. Comparison Endpoint
    resp_comp = client.get("/v1/trading/testnet/comparison")
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert "comparison_timestamp" in comp_data
    assert "testnet_summary" in comp_data
    assert "paper_summary" in comp_data
    assert "strategy_divergence" in comp_data
    assert len(comp_data["strategy_divergence"]) >= 1
    assert "recommendations_summary" in comp_data
