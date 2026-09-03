from __future__ import annotations

import threading
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, threshold: int = 5, recovery_seconds: float = 30.0) -> None:
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at = 0.0
        self.state = CircuitState.CLOSED
        self._lock = threading.RLock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == CircuitState.OPEN and time.monotonic() - self.opened_at >= self.recovery_seconds:
                self.state = CircuitState.HALF_OPEN
            return self.state != CircuitState.OPEN

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            self.state = CircuitState.CLOSED

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
