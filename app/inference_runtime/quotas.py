from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .errors import RateLimitExceeded


@dataclass
class Quota:
    rpm: int
    tpm: int
    requests: int = 0
    tokens: int = 0
    window_start: float = 0.0


class TenantQuotaManager:
    def __init__(self) -> None:
        self._q: dict[str, Quota] = {}
        self._lock = threading.RLock()

    def configure(self, tenant: str, rpm: int, tpm: int) -> None:
        with self._lock:
            self._q[tenant] = Quota(max(1, rpm), max(1, tpm), window_start=time.time())

    def admit(self, tenant: str, estimated_tokens: int) -> None:
        with self._lock:
            q = self._q.get(tenant)
            if q is None:
                return
            now = time.time()
            if now - q.window_start >= 60:
                q.requests = 0
                q.tokens = 0
                q.window_start = now
            if q.requests + 1 > q.rpm or q.tokens + estimated_tokens > q.tpm:
                raise RateLimitExceeded(f"quota exceeded for tenant {tenant}")
            q.requests += 1
            q.tokens += estimated_tokens
