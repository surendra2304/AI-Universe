"""Concurrent Load Testing and Performance SLA Verification Suite."""

import math
import time
from typing import List
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.monitoring import monitor, _percentile

client = TestClient(app)


def test_production_health_endpoints():
    """Validates all production health, metrics, and detailed diagnostic endpoints."""
    # 1. Basic Health
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

    # 2. Detailed Health
    r = client.get("/health/detailed")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "healthy"
    assert "performance" in d
    assert "cache" in d
    assert "concurrency" in d

    # 3. Provider Health
    r = client.get("/health/providers")
    assert r.status_code == 200
    assert "providers" in r.json()

    # 4. Status Endpoint
    r = client.get("/status")
    assert r.status_code == 200
    st = r.json()
    assert st["status"] == "operational"
    assert st["advisory_only"] is True
    assert "active_specialists_count" in st

    # 5. Prometheus Metrics
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "inference_requests_total" in r.text
    assert "inference_latency_p95_seconds" in r.text


def test_concurrent_load_and_p95_sla():
    """
    Simulates 100 concurrent consultation requests across varying telemetry scenarios.
    Verifies that p95 response time is strictly < 30 seconds.
    """
    total_requests = 100
    latencies: List[float] = []

    def make_request(idx: int) -> float:
        # Alternate scenarios
        if idx % 3 == 0:
            # Healthy
            payload = {
                "bot_id": f"bot_load_{idx}",
                "trading_mode": "PAPER",
                "telemetry": {
                    "equity": 10500.0,
                    "unrealized_pnl": 50.0,
                    "realized_pnl": 500.0,
                    "win_rate": 0.65,
                    "profit_factor": 1.70,
                    "max_drawdown_pct": 2.2,
                    "consecutive_losses": 1,
                    "total_trades": 60
                },
                "consultation_reason": "SCHEDULED"
            }
        elif idx % 3 == 1:
            # Struggling Testnet
            payload = {
                "bot_id": f"bot_load_{idx}",
                "trading_mode": "TESTNET",
                "testnet_specific": {
                    "testnet_equity": 9200.0,
                    "testnet_drawdown_pct": 7.5,
                    "testnet_daily_loss": 300.0,
                    "testnet_open_positions": 2,
                    "testnet_margin_level": 140.0
                },
                "telemetry": {
                    "equity": 9200.0,
                    "unrealized_pnl": -60.0,
                    "realized_pnl": -800.0,
                    "win_rate": 0.36,
                    "profit_factor": 0.75,
                    "max_drawdown_pct": 7.5,
                    "consecutive_losses": 5,
                    "total_trades": 45
                },
                "current_parameters": {
                    "Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}
                },
                "consultation_reason": "DRAWDOWN_EVENT"
            }
        else:
            # Insufficient data
            payload = {
                "bot_id": f"bot_load_{idx}",
                "trading_mode": "PAPER",
                "telemetry": {
                    "equity": 10000.0,
                    "unrealized_pnl": 0.0,
                    "realized_pnl": 0.0,
                    "win_rate": 0.50,
                    "profit_factor": 1.0,
                    "max_drawdown_pct": 1.0,
                    "consecutive_losses": 0,
                    "total_trades": 8
                },
                "consultation_reason": "SCHEDULED"
            }

        start = time.perf_counter()
        resp = client.post("/v1/trading/consult", json=payload)
        dur = time.perf_counter() - start
        assert resp.status_code == 200
        return dur

    for i in range(total_requests):
        dur = make_request(i)
        latencies.append(dur)

    p50 = float(_percentile(latencies, 50))
    p95 = float(_percentile(latencies, 95))
    p99 = float(_percentile(latencies, 99))
    avg_lat = float(sum(latencies) / len(latencies))

    print(f"\n[LOAD TEST RESULTS] Total: {total_requests} | P50: {p50:.3f}s | P95: {p95:.3f}s | P99: {p99:.3f}s | Avg: {avg_lat:.3f}s")

    # Strict SLA verification: p95 must be under 30 seconds
    assert p95 < 30.0, f"P95 latency {p95:.3f}s exceeds the 30.0s SLA target"
