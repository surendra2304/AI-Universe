"""Concurrent Dual-Arm Load Testing for A/B Trading Consultation."""

import asyncio
import time

import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_dual_arm_simultaneous_consultations():
    """
    Sends simultaneous consultation requests from both CONTROL and TREATMENT arms.
    Verifies:
    1. Simultaneous dual-arm execution succeeds with HTTP 200.
    2. Independent rate limiter tracking per bot_id (no false positive 429s).
    3. Proper A/B decision payload formatting under concurrency.
    """
    exp_id = "exp_dual_load_test"
    num_pairs = 15  # 15 pairs = 30 simultaneous consultations

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Register experiment
        reg_resp = await client.post("/v1/trading/experiment/start", json={
            "experiment_id": exp_id,
            "control_bot_id": "dual_ctrl_master",
            "treatment_bot_id": "dual_treat_master",
            "duration_hours": 48.0
        })
        assert reg_resp.status_code == 201

        # 2. Prepare simultaneous requests for pairs of control & treatment bots
        tasks = []
        for i in range(num_pairs):
            ctrl_bot = f"dual_ctrl_{i:03d}"
            treat_bot = f"dual_treat_{i:03d}"

            ctrl_payload = {
                "bot_id": ctrl_bot,
                "trading_mode": "PAPER",
                "experiment_id": exp_id,
                "experiment_group": "CONTROL",
                "telemetry": {
                    "equity": 10000.0,
                    "unrealized_pnl": 0.0,
                    "realized_pnl": 200.0,
                    "win_rate": 0.55,
                    "profit_factor": 1.35,
                    "max_drawdown_pct": 3.5,
                    "consecutive_losses": 1,
                    "total_trades": 35
                },
                "consultation_reason": "SCHEDULED"
            }

            treat_payload = {
                "bot_id": treat_bot,
                "trading_mode": "PAPER",
                "experiment_id": exp_id,
                "experiment_group": "TREATMENT",
                "control_metrics": {
                    "profit_factor": 1.35,
                    "win_rate": 0.55,
                    "max_drawdown_pct": 3.5,
                    "total_trades": 35
                },
                "telemetry": {
                    "equity": 9500.0,
                    "unrealized_pnl": -50.0,
                    "realized_pnl": -500.0,
                    "win_rate": 0.38,
                    "profit_factor": 0.78,
                    "max_drawdown_pct": 7.8,
                    "consecutive_losses": 4,
                    "total_trades": 32
                },
                "current_parameters": {
                    "Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}
                },
                "consultation_reason": "DRAWDOWN_EVENT"
            }

            tasks.append(client.post("/v1/trading/consult", json=ctrl_payload))
            tasks.append(client.post("/v1/trading/consult", json=treat_payload))

        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        # 3. Assert all 30 simultaneous requests succeeded
        assert len(responses) == num_pairs * 2
        for resp in responses:
            assert resp.status_code == 200, f"Request failed: {resp.text}"
            data = resp.json()
            assert data["status"] in ["NO_CHANGE", "RECOMMENDATION"]
            assert data["decision_id"] is not None

        # 4. Check experiment status records all consultations
        status_resp = await client.get(f"/v1/trading/experiment/{exp_id}/status")
        assert status_resp.status_code == 200
        st = status_resp.json()
        assert st["consultations_count"]["CONTROL"] == num_pairs
        assert st["consultations_count"]["TREATMENT"] == num_pairs

        print(f"\n[+] Dual-Arm Load Test: {len(responses)} concurrent requests completed in {total_time:.2f}s")
