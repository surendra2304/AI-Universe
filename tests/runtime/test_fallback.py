import pytest

from app.inference_runtime.contracts import Capability, CompletionRequest, Message, ProviderEndpoint
from app.inference_runtime.fallback_executor import FallbackExecutor


@pytest.mark.asyncio
async def test_fallback_executor_skips_failure():
    f = FallbackExecutor()
    eps = [
        ProviderEndpoint("bad", "m", frozenset({Capability.CHAT})),
        ProviderEndpoint("good", "m", frozenset({Capability.CHAT})),
    ]
    calls = []

    async def call(ep):
        calls.append(ep.provider)
        if ep.provider == "bad":
            raise RuntimeError("503")
        return "ok"

    assert await f.run(CompletionRequest("m", (Message("user", "x"),)), eps, call) == "ok"
    assert calls == ["bad", "good"]
