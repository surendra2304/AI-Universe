from __future__ import annotations

import threading

from .errors import BudgetExceeded


class BudgetLedger:
    def __init__(self, default_budget: float = 10.0) -> None:
        self.default = default_budget
        self._spent: dict[tuple[str, str], float] = {}
        self._reserved: dict[tuple[str, str], float] = {}
        self._lock = threading.RLock()

    def _key(self, tenant: str, period: str) -> tuple[str, str]:
        return tenant, period

    def remaining(self, tenant: str, period: str = "current") -> float:
        with self._lock:
            return (
                self.default
                - self._spent.get(self._key(tenant, period), 0.0)
                - self._reserved.get(self._key(tenant, period), 0.0)
            )

    def reserve(self, tenant: str, amount: float, period: str = "current") -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        with self._lock:
            k = self._key(tenant, period)
            available = self.default - self._spent.get(k, 0.0) - self._reserved.get(k, 0.0)
            if amount > available:
                raise BudgetExceeded(f"Budget exceeded for tenant {tenant}: need {amount:.6f}, have {available:.6f}")
            self._reserved[k] = self._reserved.get(k, 0.0) + amount

    def reconcile(self, tenant: str, estimated: float, actual: float, period: str = "current") -> None:
        with self._lock:
            k = self._key(tenant, period)
            self._reserved[k] = max(0.0, self._reserved.get(k, 0.0) - estimated)
            self._spent[k] = self._spent.get(k, 0.0) + actual
