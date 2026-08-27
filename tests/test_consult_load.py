"""Load and Stress Testing for AI Universe Trading Consultation Endpoint."""

import asyncio
import statistics
import time
from typing import List
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.trading_consult import AIUniverseDecision


@pytest.mark.asyncio
async def test_load_concurrent_consultations():
    """
    Load test sending 100 concurrent requests across distinct bot_ids.
    Measures latency percentiles (p50, p95, max), verifies zero false-positive 429s for unique bots,
    and ensures response integrity.
    """
    total_requests = 100
    base_payload = {
        "trading_mode": "PAPER",
        "telemetry": {
            "equity": 10000.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "win_rate": 0.55,
            "profit_factor": 1.35,
            "max_drawdown_pct": 2.5,
            "consecutive_losses": 1,
            "total_trades": 35
        },
        "consultation_reason": "SCHEDULED"
    }

    latencies: List[float] = []
    status_codes: List[int] = []
    decisions_count = 0

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        async def send_single_consultation(bot_index: int):
            bot_payload = dict(base_payload)
            bot_payload["bot_id"] = f"load_bot_{bot_index:04d}"
            start_t = time.perf_counter()
            try:
                resp = await client.post("/v1/trading/consult", json=bot_payload, timeout=180.0)
                elapsed = time.perf_counter() - start_t
                latencies.append(elapsed)
                status_codes.append(resp.status_code)
                if resp.status_code == 200:
                    data = resp.json()
                    decision = AIUniverseDecision.model_validate(data)
                    return decision
                return None
            except Exception as e:
                elapsed = time.perf_counter() - start_t
                latencies.append(elapsed)
                status_codes.append(500)
                return None

        # Execute 100 concurrent asynchronous requests in batches of 25 to balance local event loop
        batch_size = 25
        results = []
        for i in range(0, total_requests, batch_size):
            tasks = [send_single_consultation(j) for j in range(i, min(i + batch_size, total_requests))]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

    success_count = sum(1 for code in status_codes if code == 200)
    decisions_count = sum(1 for r in results if r is not None)

    assert success_count == total_requests, f"Expected 100 HTTP 200 responses, got {success_count} (Errors: {[c for c in status_codes if c != 200]})"
    assert decisions_count == total_requests, f"Expected 100 valid AIUniverseDecision objects, got {decisions_count}"

    # Calculate latency benchmarks
    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg_latency = statistics.mean(latencies)
    max_latency = max(latencies)

    print(f"\n--- LOAD & STRESS TEST BENCHMARK (N={total_requests}) ---")
    print(f"Total Requests: {total_requests}")
    print(f"Success Rate:   {success_count / total_requests * 100:.1f}%")
    print(f"Average Latency: {avg_latency:.3f}s")
    print(f"P50 Latency:     {p50:.3f}s")
    print(f"P95 Latency:     {p95:.3f}s (Threshold < 180s)")
    print(f"P99 Latency:     {p99:.3f}s")
    print(f"Max Latency:     {max_latency:.3f}s")
    print("--------------------------------------------------")

    # Assert p95 latency is strictly under 180s timeout limit
    assert p95 < 180.0, f"P95 latency {p95:.2f}s exceeded 180s timeout"
    # Ensure no false-positive 429 errors occurred for distinct bots
    assert 429 not in status_codes, "Rate limiter generated false positive 429 for unique bot_ids"
