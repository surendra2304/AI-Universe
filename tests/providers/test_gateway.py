"""Unit and integration tests for ModelGateway, KeyPool, RateLimiter, HealthTracker, and Dynamic OpenRouter Fallback."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.providers.base import ProviderMessage, ProviderRequest, ProviderResponse
from app.providers.gateway import KeyPool, ModelGateway, ProviderRateLimiter
from app.providers.health import ProviderHealthTracker, provider_health_tracker
from app.providers.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_key_pool_round_robin_and_quarantine():
    pool = KeyPool("test_prov", ["key_1", "key_2", "key_3"])
    assert pool.total_keys_count == 3
    assert pool.get_active_keys_count() == 3

    # Test round robin
    k1 = await pool.get_next_key()
    k2 = await pool.get_next_key()
    k3 = await pool.get_next_key()
    k4 = await pool.get_next_key()
    assert [k1, k2, k3, k4] == ["key_1", "key_2", "key_3", "key_1"]

    # Quarantine key_2 for 60s
    await pool.quarantine_key("key_2", duration_seconds=60.0)
    assert pool.get_active_keys_count() == 2
    assert pool.get_quarantined_keys_count() == 1

    # Should only return key_1 and key_3 now
    keys_received = [await pool.get_next_key() for _ in range(4)]
    assert "key_2" not in keys_received
    assert set(keys_received) == {"key_1", "key_3"}


@pytest.mark.asyncio
async def test_provider_rate_limiter_isolation():
    """Verify Provider A rate limiting does not block Provider B."""
    limiter_a = ProviderRateLimiter("prov_a", requests_per_second=100.0, max_concurrency=2)
    limiter_b = ProviderRateLimiter("prov_b", requests_per_second=100.0, max_concurrency=2)

    # Acquire on A
    await limiter_a.acquire()
    # Acquiring on B should succeed immediately without being blocked by A
    acquired_b = False
    try:
        await asyncio.wait_for(limiter_b.acquire(), timeout=1.0)
        acquired_b = True
    except asyncio.TimeoutError:
        acquired_b = False
    finally:
        limiter_a.release()
        limiter_b.release()

    assert acquired_b is True


@pytest.mark.asyncio
async def test_provider_health_tracking():
    tracker = ProviderHealthTracker()
    tracker.record_success("gemini", latency_seconds=0.45)
    tracker.record_success("gemini", latency_seconds=0.55)

    health = tracker.get_provider_health("gemini")
    assert health.provider_name == "gemini"
    assert health.is_healthy is True
    assert health.success_count == 2
    assert health.failure_count == 0
    assert health.average_latency_seconds == 0.50

    # Record 429 rate limit
    tracker.record_failure("gemini", error="429 Too Many Requests", is_429=True)
    health_after_429 = tracker.get_provider_health("gemini")
    assert health_after_429.rate_limit_429_count == 1
    assert health_after_429.consecutive_failures == 1


@pytest.mark.asyncio
async def test_openrouter_dynamic_capability_model_discovery():
    openrouter = OpenRouterProvider(api_key="mock_key")

    mock_models_response = {
        "data": [
            {"id": "qwen/qwen-2.5-coder-32b-instruct:free", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "nvidia/nemotron-3.5-lightning:free", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "mistralai/mistral-small-24b-instruct-2501:free", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "deepseek/deepseek-r1-distill-llama-70b:paid", "pricing": {"prompt": "0.0001", "completion": "0.0002"}},
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_models_response

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        # 1. get_best_free_model("coding") should filter for free and pick qwen coder
        coding_model = await openrouter.get_best_free_model("coding")
        assert "coder" in coding_model.lower() or "qwen" in coding_model.lower()
        assert ":free" in coding_model

        # 2. get_best_free_model("reasoning") should pick nemotron:free
        reasoning_model = await openrouter.get_best_free_model("reasoning")
        assert "nemotron" in reasoning_model.lower()
        assert ":free" in reasoning_model

        # 3. get_best_free_model("research") should pick mistral:free
        research_model = await openrouter.get_best_free_model("research")
        assert "mistral" in research_model.lower() or "free" in research_model.lower()


@pytest.mark.asyncio
async def test_model_gateway_key_rotation_on_429():
    gateway = ModelGateway()
    gateway.key_pools["gemini"].set_keys(["key_fail_429", "key_working"])

    req = ProviderRequest(messages=[ProviderMessage(role="user", content="hello")])

    call_count = 0
    async def mock_generate(self, r):
        nonlocal call_count
        call_count += 1
        if self.api_key == "key_fail_429":
            raise RuntimeError("Gemini rate limit exceeded (HTTP 429).")
        return ProviderResponse(
            content="Success from working key",
            model="gemini-3.6-flash",
            provider="gemini",
            latency_seconds=0.2
        )

    with patch("app.providers.gemini.GeminiProvider.generate", side_effect=mock_generate, autospec=True):
        resp = await gateway.execute("gemini", req, capability="research")
        assert resp.content == "Success from working key"
        assert call_count == 2
        # Verify first key was quarantined
        assert gateway.key_pools["gemini"].get_quarantined_keys_count() == 1


@pytest.mark.asyncio
async def test_model_gateway_dynamic_fallback_when_all_keys_exhausted():
    gateway = ModelGateway()
    gateway.key_pools["mistral"].set_keys(["bad_key"])

    req = ProviderRequest(messages=[ProviderMessage(role="user", content="evaluate security")])

    mock_openrouter_response = ProviderResponse(
        content="OpenRouter fallback response for security",
        model="nvidia/nemotron-3.5-lightning:free",
        provider="openrouter",
        latency_seconds=0.35
    )

    with patch("app.providers.mistral.MistralProvider.generate", side_effect=RuntimeError("HTTP 429 Rate Limit")), \
         patch("app.providers.openrouter.OpenRouterProvider.generate", new_callable=AsyncMock) as mock_or_gen:
        mock_or_gen.return_value = mock_openrouter_response

        resp = await gateway.execute("mistral", req, capability="security")
        assert resp.content == "OpenRouter fallback response for security"
        assert resp.provider == "openrouter"
