from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .contracts import ProviderEndpoint


@dataclass
class ModelRecord:
    endpoint: ProviderEndpoint
    enabled: bool = True
    aliases: set[str] = field(default_factory=set)
    metadata: dict[str, object] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[tuple[str, str], ModelRecord] = {}
        self._aliases: dict[str, tuple[str, str]] = {}
        self._lock = threading.RLock()

    def upsert(self, record: ModelRecord) -> None:
        with self._lock:
            self._models[(record.endpoint.provider, record.endpoint.model)] = record
            for a in record.aliases:
                self._aliases[a] = (record.endpoint.provider, record.endpoint.model)

    def disable(self, provider: str, model: str) -> None:
        with self._lock:
            if r := self._models.get((provider, model)):
                r.enabled = False
                r.updated_at = time.time()

    def resolve(self, name: str, provider: str | None = None) -> ModelRecord | None:
        with self._lock:
            key = self._aliases.get(name)
            if key:
                return self._models.get(key)
            candidates = [
                r
                for r in self._models.values()
                if r.endpoint.model == name and (provider is None or r.endpoint.provider == provider)
            ]
            return next((r for r in candidates if r.enabled), None)

    def list_enabled(self) -> list[ModelRecord]:
        with self._lock:
            return [r for r in self._models.values() if r.enabled]
