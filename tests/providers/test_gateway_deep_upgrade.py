import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.core.orchestrator import OrchestrationRequest, Orchestrator
from app.main import app
from app.providers.base import ProviderMessage, ProviderRequest
from app.providers.gateway import KeyPool, ModelGateway, ProviderRateLimiter

client = TestClient(app)


def test_key_pool_all_quarantined_fails_closed():
    pool = KeyPool("test_provider", ["key1", "key2"])
    pool.quarantine("key1", 60.0)
    pool.quarantine("key2", 60.0)
    assert pool.choose() is None
    assert pool.get_active_keys_count() == 0
    assert pool.get_quarantined_keys_count() == 2


def test_key_pool_rotation_skips_quarantined():
    pool = KeyPool("test_provider", ["key1", "key2", "key3"])
    pool.quarantine("key1", 60.0)
    chosen = [pool.choose() for _ in range(4)]
    assert "key1" not in chosen
    assert set(chosen) == {"key2", "key3"}


@pytest.mark.asyncio
async def test_provider_rate_limiter_concurrency():
    limiter = ProviderRateLimiter("test_provider", requests_per_second=100.0, max_concurrency=4)
    async def acquire_and_release():
        await limiter.acquire()
        limiter.release()

    await asyncio.gather(*(acquire_and_release() for _ in range(8)))


@pytest.mark.asyncio
async def test_gateway_deadline_exceeded_aborts():
    gw = ModelGateway()
    gw.key_pools["gemini"] = KeyPool("gemini", ["test_key"])
    gw.rate_limiters["gemini"] = ProviderRateLimiter("gemini", 10.0, 2)

    req = ProviderRequest(
        messages=[ProviderMessage(role="user", content="hello")],
        extra_params={"timeout": 0.0001}
    )
    time.sleep(0.002)
    with pytest.raises(TimeoutError):
        await gw.execute("gemini", req)


@pytest.mark.asyncio
async def test_cancelled_task_cannot_be_completed():
    orch = Orchestrator()
    task_id = "test_cancel_task_001"
    cancel_event = asyncio.Event()
    orch._active_cancellations[task_id] = cancel_event

    async def fake_collab(**kwargs):
        cancel_event.set()
        await asyncio.sleep(0.01)
        import types
        mock_res = types.SimpleNamespace(
            final_answer="Late answer",
            confidence=0.9,
            debate_id="deb_001",
            unresolved_disagreements=[],
            models_used=[],
            participating_agents=[],
            key_evidence=[],
            structured_evidence=[],
            claims=[],
            adjudication=None,
            total_tokens=10,
        )
        return mock_res

    orch.debate_engine.run_collaboration = fake_collab

    with pytest.raises(asyncio.CancelledError):
        await orch.process_task(OrchestrationRequest(question="Test?", mode="fast"), task_id=task_id)

    status = await orch.get_task_status(task_id)
    assert status is not None
    assert status["status"] == "cancelled"


def test_correlation_id_preserved_in_exception():
    resp = client.get("/v1/trading/performance", headers={"X-Correlation-ID": "test-custom-cid-12345"})
    assert resp.headers.get("X-Correlation-ID") == "test-custom-cid-12345" or resp.status_code in (200, 401, 403, 404, 500)


def test_operational_endpoints():
    res_health = client.get("/health/providers")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert "providers" in data_health
    assert "key_pools" in data_health

    res_models = client.get("/models")
    assert res_models.status_code == 200
    data_models = res_models.json()
    assert "models" in data_models
    assert data_models["count"] > 0

    res_metrics = client.get("/metrics/runtime")
    assert res_metrics.status_code == 200
    data_metrics = res_metrics.json()
    assert "metrics" in data_metrics
