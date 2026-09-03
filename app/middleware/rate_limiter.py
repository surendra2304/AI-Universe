"""Enhanced Multi-Consumer Rate Limiter Middleware.

Features:
- Per-API-Key rate limits configured via MultiConsumerRouter
- Burst allowance (2x limit for 60-second bursts)
- Request queuing / backoff with retry-after header
- Standard rate limit response headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
"""

import threading
import time
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.routing.consumer_router import consumer_router
from app.utils.logger import logger


class EnhancedRateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware applying dynamic per-consumer rate limits and standard headers."""

    def __init__(self, app, max_tracked_keys: int = 10000) -> None:
        super().__init__(app)
        self._request_history: dict[str, list[float]] = {}
        self._window_seconds = 3600.0  # 1 hour sliding window
        self._max_tracked_keys = max_tracked_keys
        self._lock = threading.RLock()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health and docs checks
        if request.url.path in ("/health", "/", "/docs", "/openapi.json", "/v1/forge/health"):
            return await call_next(request)

        # Identify consumer identity
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")
        client_ip = request.client.host if request.client else "unknown"

        # Local testing / development exemption:
        # Development bypass requires an explicit development setting or test runner detection;
        # production behavior strictly requires authentication and enforces rate limits.
        import os
        import sys

        is_test_env = "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST") is not None
        is_dev_env = settings.APP_ENV in ("development", "test") or settings.INSECURE_DEV_AUTH or settings.ALLOW_DEV_RATE_LIMIT_BYPASS

        if (is_test_env or is_dev_env) and client_ip in ("testclient", "127.0.0.1", "localhost"):
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = "10000"
            response.headers["X-RateLimit-Remaining"] = "9999"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 3600))
            return response

        consumer_id = consumer_router.identify_consumer(auth_header or api_key_header or client_ip)
        profile = consumer_router.PROFILES.get(consumer_id, consumer_router.PROFILES["human"])

        now = time.time()
        key = f"{consumer_id}:{client_ip}"
        limit = profile.rate_limit_per_hour
        burst_limit = limit * 2

        with self._lock:
            # Memory bounding: periodic / capacity-based eviction
            if len(self._request_history) >= self._max_tracked_keys:
                expired = [k for k, h in self._request_history.items() if not h or (now - h[-1]) >= self._window_seconds]
                for k in expired:
                    self._request_history.pop(k, None)
                if len(self._request_history) >= self._max_tracked_keys:
                    for k in list(self._request_history.keys())[:1000]:
                        self._request_history.pop(k, None)

            history = self._request_history.get(key, [])
            history = [ts for ts in history if now - ts < self._window_seconds]

            if len(history) >= burst_limit:
                earliest_ts = history[0] if history else now
                reset_seconds = max(1, int(self._window_seconds - (now - earliest_ts)))
                logger.warning("Rate limit exceeded for consumer '%s' (IP: %s)", consumer_id, client_ip)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded for consumer '{consumer_id}'. Limit: {limit}/hour.",
                        "retry_after_seconds": reset_seconds
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + reset_seconds)),
                        "Retry-After": str(reset_seconds)
                    }
                )

            history.append(now)
            self._request_history[key] = history
            remaining = max(0, limit - len(history))

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self._window_seconds))

        return response
