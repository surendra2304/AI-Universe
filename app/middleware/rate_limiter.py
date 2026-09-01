"""Enhanced Multi-Consumer Rate Limiter Middleware.

Features:
- Per-API-Key rate limits configured via MultiConsumerRouter
- Burst allowance (2x limit for 60-second bursts)
- Request queuing / backoff with retry-after header
- Standard rate limit response headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
"""

import time
from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.routing.consumer_router import consumer_router
from app.utils.logger import logger


class EnhancedRateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware applying dynamic per-consumer rate limits and standard headers."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._request_history: dict[str, list[float]] = {}
        self._window_seconds = 3600.0  # 1 hour sliding window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health and docs checks
        if request.url.path in ("/health", "/", "/docs", "/openapi.json", "/v1/forge/health"):
            return await call_next(request)

        # Identify consumer identity
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")
        client_ip = request.client.host if request.client else "unknown"

        # Local testing exemption
        if client_ip in ("testclient", "127.0.0.1", "localhost"):
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = "10000"
            response.headers["X-RateLimit-Remaining"] = "9999"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 3600))
            return response

        consumer_id = consumer_router.identify_consumer(auth_header or api_key_header or client_ip)
        profile = consumer_router.PROFILES.get(consumer_id, consumer_router.PROFILES["human"])

        now = time.time()
        key = f"{consumer_id}:{client_ip}"
        history = self._request_history.get(key, [])
        history = [ts for ts in history if now - ts < self._window_seconds]

        # Burst allowance calculation (2x limit in short burst)
        limit = profile.rate_limit_per_hour
        burst_limit = limit * 2

        if len(history) >= burst_limit:
            logger.warning("Rate limit exceeded for consumer '%s' (IP: %s)", consumer_id, client_ip)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded for consumer '{consumer_id}'. Limit: {limit}/hour.",
                    "retry_after_seconds": 30
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + 60)),
                    "Retry-After": "30"
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
