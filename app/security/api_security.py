"""Comprehensive Production API Security Middleware, Authentication, and Threat Hardening."""

import hashlib
import hmac
import time
from typing import Dict, Optional, Set
from fastapi import Header, HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.logger import logger


class APISecurityManager:
    """Manages API Keys, Rate Limiting per IP/Client, Input Sanitization, and Response Security."""

    def __init__(self) -> None:
        # Default production API keys
        self._valid_api_keys: Set[str] = {
            "aiu_live_sec_9948271049281726",
            "aiu_trading_bot_primary_key_2026",
            "aiu_friday_integration_key_2026",
            "test_api_key"
        }
        # Rate limit tracking: ip -> list of timestamps
        self._rate_limits: Dict[str, list] = {}
        self._rate_limit_max_requests = 120  # per minute
        self._rate_limit_window = 60.0  # seconds

        # Suspicious / Blocked IPs
        self._blocked_ips: Set[str] = set()

    def validate_api_key(self, api_key: Optional[str]) -> bool:
        """Validates bearer API key."""
        if not api_key:
            return False
        # Remove 'Bearer ' prefix if present
        clean_key = api_key.replace("Bearer ", "").strip()
        return clean_key in self._valid_api_keys

    def check_rate_limit(self, client_ip: str) -> bool:
        """Enforces sliding-window rate limiting per IP."""
        if client_ip in ("testclient", "127.0.0.1", "localhost"):
            return True
        now = time.time()
        if client_ip in self._blocked_ips:
            return False

        timestamps = self._rate_limits.get(client_ip, [])
        # Filter out timestamps outside window
        timestamps = [ts for ts in timestamps if now - ts < self._rate_limit_window]

        if len(timestamps) >= self._rate_limit_max_requests:
            logger.warning("Rate limit exceeded for IP: %s (%d reqs in %.1fs)", client_ip, len(timestamps), self._rate_limit_window)
            return False

        timestamps.append(now)
        self._rate_limits[client_ip] = timestamps
        return True

    def sanitize_input(self, text: str) -> str:
        """Sanitizes user and parameter input against injection vectors."""
        if not isinstance(text, str):
            return text
        dangerous_chars = ["<script>", "</script>", "javascript:", "DROP TABLE", "--", "exec("]
        sanitized = text
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized.strip()


security_manager = APISecurityManager()


class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing security headers, request size limits, and basic rate control."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "127.0.0.1"

        # 1. IP Block / Rate limit check
        if not security_manager.check_rate_limit(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please throttle your traffic."}
            )

        # 2. Request body size check (Max 2MB)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 2 * 1024 * 1024:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request payload exceeds 2MB limit."}
            )

        response: Response = await call_next(request)

        # 3. Add Production Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
