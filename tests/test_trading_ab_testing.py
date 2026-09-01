"""Integration and unit tests for A/B Testing Consultation capabilities."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ab_experiment_lifecycle():
    """Tests full A/B experiment lifecycle: start -> consult both arms -> status -> results."""
    exp_id = "exp_ab_volatility_v1"

    # 1. Start Experiment
    start_payload = {
        "experiment_id": exp_id,
        "hypothesis": "Tighter trailing stop losses reduce drawdown in choppy volatility without hurting profit factor.",
        "duration_hours": 48.0,
        "success_metrics": ["profit_factor", "max_drawdown_pct", "win_rate"],
        "control_bot_id": "bot_ctrl_01",
        "treatment_bot_id": "bot_treat_01",
        "initial_parameters": {
            "Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}
        }
    }
    resp = client.post("/v1/trading/experiment/start", json=start_payload)
    assert resp.status_code == 201
    start_data = resp.json()
    assert start_data["experiment_id"] == exp_id
    assert start_data["status"] == "ACTIVE"
    assert start_data["control_config"]["bot_id"] == "bot_ctrl_01"
    assert start_data["treatment_config"]["bot_id"] == "bot_treat_01"

    # 2. Consult CONTROL Arm (Baseline)
    control_telem = {
        "bot_id": "bot_ctrl_01",
        "trading_mode": "PAPER",
        "experiment_id": exp_id,
        "experiment_group": "CONTROL",
        "telemetry": {
            "equity": 10000.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 350.0,
            "win_rate": 0.58,
            "profit_factor": 1.45,
            "max_drawdown_pct": 3.2,
            "consecutive_losses": 1,
            "total_trades": 45
        },
        "current_parameters": {
            "Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}
        },
        "consultation_reason": "SCHEDULED"
    }
    resp_ctrl = client.post("/v1/trading/consult", json=control_telem)
    assert resp_ctrl.status_code == 200
    ctrl_decision = resp_ctrl.json()
    assert ctrl_decision["status"] in ["NO_CHANGE", "RECOMMENDATION"]
    assert ctrl_decision["treatment_status"] == "CONTROL_BASELINE"
    assert ctrl_decision["comparison_rationale"] is not None

    # 3. Consult TREATMENT Arm (underperforming relative to control)
    treatment_telem = {
        "bot_id": "bot_treat_01",
        "trading_mode": "PAPER",
        "experiment_id": exp_id,
        "experiment_group": "TREATMENT",
        "control_metrics": {
            "profit_factor": 1.45,
            "win_rate": 0.58,
            "max_drawdown_pct": 3.2,
            "total_trades": 45
        },
        "telemetry": {
            "equity": 9200.0,
            "unrealized_pnl": -80.0,
            "realized_pnl": -800.0,
            "win_rate": 0.36,
            "profit_factor": 0.72,
            "max_drawdown_pct": 8.5,
            "consecutive_losses": 5,
            "total_trades": 42
        },
        "current_parameters": {
            "Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}
        },
        "consultation_reason": "DRAWDOWN_EVENT"
    }
    resp_treat = client.post("/v1/trading/consult", json=treatment_telem)
    assert resp_treat.status_code == 200
    treat_decision = resp_treat.json()
    assert treat_decision["status"] == "RECOMMENDATION"
    assert treat_decision["treatment_status"] == "UNDERPERFORMING_CONTROL"
    assert "UNDERPERFORMING CONTROL" in treat_decision["comparison_rationale"].upper() or "CONTROL" in treat_decision["comparison_rationale"].upper()
    assert treat_decision["expected_improvement"] is not None

    # 4. Check Experiment Status
    resp_status = client.get(f"/v1/trading/experiment/{exp_id}/status")
    assert resp_status.status_code == 200
    status_data = resp_status.json()
    assert status_data["experiment_id"] == exp_id
    assert status_data["consultations_count"]["CONTROL"] == 1
    assert status_data["consultations_count"]["TREATMENT"] == 1

    # 5. Check Experiment Results
    resp_results = client.get(f"/v1/trading/experiment/{exp_id}/results")
    assert resp_results.status_code == 200
    results_data = resp_results.json()
    assert results_data["experiment_id"] == exp_id
    assert results_data["winner"] == "CONTROL"  # Control had PF 1.45 vs Treatment 0.72
    assert "CONTROL baseline outperformed Treatment" in results_data["conclusion"] or "Control" in results_data["conclusion"]


def test_ab_treatment_outperforming_scenario():
    """Tests A/B consultation when Treatment arm outperforms Control."""
    exp_id = "exp_ab_winner_treat"

    # Start experiment
    client.post("/v1/trading/experiment/start", json={
        "experiment_id": exp_id,
        "control_bot_id": "bot_ctrl_02",
        "treatment_bot_id": "bot_treat_02",
        "duration_hours": 24.0
    })

    # Consult Treatment arm with superior metrics
    treatment_telem = {
        "bot_id": "bot_treat_02",
        "trading_mode": "PAPER",
        "experiment_id": exp_id,
        "experiment_group": "TREATMENT",
        "control_metrics": {
            "profit_factor": 1.20,
            "win_rate": 0.50,
            "max_drawdown_pct": 4.5,
            "total_trades": 35
        },
        "telemetry": {
            "equity": 11500.0,
            "unrealized_pnl": 120.0,
            "realized_pnl": 1500.0,
            "win_rate": 0.65,
            "profit_factor": 2.10,
            "max_drawdown_pct": 2.0,
            "consecutive_losses": 0,
            "total_trades": 40
        },
        "consultation_reason": "SCHEDULED"
    }
    resp = client.post("/v1/trading/consult", json=treatment_telem)
    assert resp.status_code == 200
    decision = resp.json()
    assert decision["treatment_status"] == "OUTPERFORMING_CONTROL"
    assert "OUTPERFORMING" in decision["comparison_rationale"].upper()
