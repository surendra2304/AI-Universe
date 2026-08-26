"""Provider Gateway Subsystem for AI Universe.

Features:
- Global Key Pool with Round-Robin key rotation per provider.
- Per-Provider Rate Limiting (Token Bucket / Concurrency Limiter) with complete provider isolation.
- Automatic 60-second key blacklisting/quarantine on 429/503.
- Provider Health Tracking integration.
- Dynamic Capability-Based OpenRouter fallback.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.policies import ProviderSwitchingPolicy, SwitchReason
from app.providers import get_provider
from app.providers.base import BaseLLMProvider, ProviderMessage, ProviderRequest, ProviderResponse
from app.providers.health import provider_health_tracker
from app.providers.openrouter import OpenRouterProvider
from app.utils.logger import logger


class KeyPool:
    """Manages round-robin key rotation and 60-second quarantines for a provider."""

    def __init__(self, provider_name: str, keys: Optional[List[str]] = None) -> None:
        self.provider_name = provider_name.lower().strip()
        self._keys: List[str] = keys or []
        self._index: int = 0
        self._quarantined_until: Dict[str, float] = {}  # key -> timestamp until quarantined
        self._lock = asyncio.Lock()

    def set_keys(self, keys: List[str]) -> None:
        """Update active keys for this pool."""
        self._keys = [k.strip() for k in keys if k.strip()]
        self._index = 0

    @property
    def total_keys_count(self) -> int:
        return len(self._keys)

    def get_active_keys_count(self) -> int:
        now = time.time()
        return sum(1 for k in self._keys if self._quarantined_until.get(k, 0) <= now)

    def get_quarantined_keys_count(self) -> int:
        now = time.time()
        return sum(1 for k in self._keys if self._quarantined_until.get(k, 0) > now)

    async def get_next_key(self) -> Optional[str]:
        """
        Returns the next available un-quarantined key in round-robin sequence.
        If all keys are quarantined, returns the key with the earliest expiration.
        """
        async with self._lock:
            if not self._keys:
                return None

            now = time.time()
            # Clean up expired quarantines
            for k in list(self._quarantined_until.keys()):
                if self._quarantined_until[k] <= now:
                    del self._quarantined_until[k]

            # Try to find an unquarantined key starting from current index
            for _ in range(len(self._keys)):
                key = self._keys[self._index % len(self._keys)]
                self._index = (self._index + 1) % len(self._keys)
                if key not in self._quarantined_until:
                    return key

            # If all are quarantined, find the one that expires soonest
            earliest_key = min(self._keys, key=lambda k: self._quarantined_until.get(k, 0))
            return earliest_key

    async def quarantine_key(self, key: str, duration_seconds: float = 60.0) -> None:
        """Blacklist a key temporarily due to 429 rate limit or 503 service error."""
        async with self._lock:
            self._quarantined_until[key] = time.time() + duration_seconds
            masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
            logger.warning(
                "KEY POOL: Quarantining key '%s' on provider '%s' for %.0fs",
                masked_key, self.provider_name, duration_seconds
            )


class ProviderRateLimiter:
    """Per-provider token bucket and concurrency limiter guaranteeing provider isolation."""

    def __init__(self, provider_name: str, requests_per_second: float = 5.0, max_concurrency: int = 4) -> None:
        self.provider_name = provider_name
        self.rate = requests_per_second
        self.max_tokens = float(max_concurrency * 2)
        self.tokens = self.max_tokens
        self.last_update = time.time()
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a rate limit token and semaphore slot asynchronously."""
        await self.semaphore.acquire()
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.max_tokens, self.tokens + (elapsed * self.rate))

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0

    def release(self) -> None:
        """Release the concurrency semaphore slot."""
        self.semaphore.release()


class ModelGateway:
    """
    Central gateway coordinating LLM calls with:
    - Per-provider rate limiting & isolation.
    - Round-robin key rotation with 60s quarantine on 429/503.
    - Provider health tracking.
    - Dynamic capability-based OpenRouter fallback.
    """

    def __init__(self) -> None:
        self.key_pools: Dict[str, KeyPool] = {}
        self.rate_limiters: Dict[str, ProviderRateLimiter] = {}
        self.health_tracker = provider_health_tracker
        self._initialize_pools()

    def _initialize_pools(self) -> None:
        """Initialize key pools and rate limiters for all known providers."""
        all_providers = ["gemini", "groq", "mistral", "openrouter", "cohere", "huggingface", "nvidia"]
        for prov in all_providers:
            keys = settings.get_provider_keys(prov)
            self.key_pools[prov] = KeyPool(prov, keys)
            # Default rate limits per provider
            rpm = 10.0 if prov in ("gemini", "cohere") else 20.0
            self.rate_limiters[prov] = ProviderRateLimiter(prov, requests_per_second=rpm / 60.0, max_concurrency=4)

    def refresh_keys(self) -> None:
        """Reload keys from environment/settings."""
        for prov, pool in self.key_pools.items():
            keys = settings.get_provider_keys(prov)
            pool.set_keys(keys)

    def get_provider_health(self, provider_name: str) -> Any:
        """Return live health metrics for a provider."""
        pool = self.key_pools.get(provider_name.lower())
        if pool:
            self.health_tracker.update_key_counts(
                provider_name,
                active_count=pool.get_active_keys_count(),
                quarantined_count=pool.get_quarantined_keys_count()
            )
        return self.health_tracker.get_provider_health(provider_name)

    async def execute(
        self,
        provider_name: str,
        request: ProviderRequest,
        capability: str = "general",
        stage_name: str = "general"
    ) -> ProviderResponse:
        """
        Executes an LLM request through the gateway:
        1. Selects key from round-robin pool.
        2. Applies isolated per-provider rate limiter.
        3. Retries across alternate keys if 429 or 503 is encountered.
        4. If all keys exhausted, falls back to dynamic capability-matched OpenRouter model.
        5. Updates health metrics.
        """
        prov_name = provider_name.lower().strip()
        pool = self.key_pools.get(prov_name)
        if not pool or pool.total_keys_count == 0:
            # Refresh in case settings were updated dynamically
            keys = settings.get_provider_keys(prov_name)
            if keys:
                if not pool:
                    pool = KeyPool(prov_name, keys)
                    self.key_pools[prov_name] = pool
                else:
                    pool.set_keys(keys)

        limiter = self.rate_limiters.get(prov_name)
        if not limiter:
            limiter = ProviderRateLimiter(prov_name)
            self.rate_limiters[prov_name] = limiter

        # Attempt execution across keys in the pool
        attempts = max(1, pool.total_keys_count if pool else 1)
        last_error = None
        current_key = None

        for _ in range(attempts):
            current_key = await pool.get_next_key() if pool else None
            start_time = time.perf_counter()

            try:
                # Instantiate or retrieve provider instance with the selected key
                import app.providers
                provider_instance = app.providers.get_provider(prov_name, api_key=current_key) if current_key else app.providers.get_provider(prov_name)

                # Acquire isolated rate limiter slot
                await limiter.acquire()
                try:
                    resp = await provider_instance.generate(request)
                finally:
                    limiter.release()

                latency = time.perf_counter() - start_time
                self.health_tracker.record_success(prov_name, latency)
                return resp

            except Exception as exc:
                latency = time.perf_counter() - start_time
                last_error = exc
                err_str = str(exc)
                is_429 = "429" in err_str or "rate limit" in err_str.lower()
                is_503 = "503" in err_str or "unavailable" in err_str.lower() or "overloaded" in err_str.lower()

                self.health_tracker.record_failure(prov_name, err_str, is_429=is_429, is_503=is_503, latency_seconds=latency)

                if current_key and (is_429 or is_503):
                    await pool.quarantine_key(current_key, duration_seconds=60.0)
                    logger.warning(
                        "GATEWAY: Provider '%s' hit rate limit/error. Rotating to next key in pool. Error: %s",
                        prov_name, err_str.split("\n")[0]
                    )
                    await asyncio.sleep(0.5)
                    continue
                else:
                    # Non-retriable or single-key failure
                    break

        # Primary provider failed on all keys -> Fallback logic
        logger.warning(
            "GATEWAY: Primary provider '%s' failed on all keys. Initiating dynamic fallback for capability '%s'.",
            prov_name, capability
        )

        fallback_resp = await self._execute_dynamic_fallback(
            failed_provider=prov_name,
            request=request,
            capability=capability,
            stage_name=stage_name,
            last_error=last_error
        )
        return fallback_resp

    async def _execute_dynamic_fallback(
        self,
        failed_provider: str,
        request: ProviderRequest,
        capability: str,
        stage_name: str,
        last_error: Optional[Exception]
    ) -> ProviderResponse:
        """Executes fallback via OpenRouter with dynamic capability matching or policy matrix."""
        # 1. If failed provider is NOT openrouter, use OpenRouter with dynamic capability model discovery
        if failed_provider != "openrouter":
            try:
                import app.providers
                openrouter_prov = app.providers.get_provider("openrouter")
                if hasattr(openrouter_prov, "get_best_free_model"):
                    dynamic_model = await openrouter_prov.get_best_free_model(capability)
                elif hasattr(openrouter_prov, "find_model_by_capability"):
                    dynamic_model = await openrouter_prov.find_model_by_capability(capability)
                else:
                    dynamic_model = "nvidia/nemotron-3.5-lightning:free"

                logger.info(
                    "GATEWAY FALLBACK: Routed to OpenRouter (Dynamic Model: %s) for capability '%s'",
                    dynamic_model, capability
                )

                fallback_req = ProviderRequest(
                    messages=request.messages,
                    system_instruction=request.system_instruction,
                    model=dynamic_model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens or 1024,
                    response_schema=request.response_schema,
                    extra_params=request.extra_params
                )

                openrouter_limiter = self.rate_limiters.get("openrouter") or ProviderRateLimiter("openrouter")
                await openrouter_limiter.acquire()
                try:
                    resp = await openrouter_prov.generate(fallback_req)
                finally:
                    openrouter_limiter.release()

                self.health_tracker.record_success("openrouter", resp.latency_seconds)
                return resp

            except Exception as fb_exc:
                logger.error("OpenRouter dynamic fallback failed: %s", str(fb_exc))

        # 2. Check standard policy matrix fallback as second safeguard
        fallback_route = ProviderSwitchingPolicy.get_fallback_provider(
            failed_provider, SwitchReason.TIMEOUT, stage=stage_name
        )
        if fallback_route and fallback_route.fallback_provider != failed_provider:
            try:
                import app.providers
                sec_prov = app.providers.get_provider(fallback_route.fallback_provider)
                sec_req = ProviderRequest(
                    messages=request.messages,
                    system_instruction=request.system_instruction,
                    model=fallback_route.fallback_model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens or 1024
                )
                return await sec_prov.generate(sec_req)
            except Exception as sec_exc:
                logger.error("Secondary fallback provider '%s' failed: %s", fallback_route.fallback_provider, str(sec_exc))

        # If all fallbacks failed, raise the original error
        if last_error:
            raise last_error
        raise RuntimeError(f"Provider {failed_provider} and all fallback routes failed.")


# Global default gateway instance
model_gateway = ModelGateway()
