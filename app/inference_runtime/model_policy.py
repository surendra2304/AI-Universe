from __future__ import annotations

from dataclasses import dataclass

from .contracts import Capability, CompletionRequest, ProviderEndpoint


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str


class ModelPolicy:
    def __init__(self, deny_models: set[str] | None = None, max_context: int = 1_000_000):
        self.deny = deny_models or set()
        self.max_context = max_context

    def check(self, request: CompletionRequest, endpoint: ProviderEndpoint) -> PolicyResult:
        if endpoint.model in self.deny:
            return PolicyResult(False, "model denied by policy")
        if endpoint.max_context > self.max_context:
            return PolicyResult(False, "advertised context exceeds configured safety bound")
        if request.response_schema and Capability.JSON not in endpoint.capabilities:
            return PolicyResult(False, "structured output capability not declared")
        if request.stream and Capability.STREAM not in endpoint.capabilities:
            return PolicyResult(False, "stream capability not declared")
        return PolicyResult(True, "ok")
