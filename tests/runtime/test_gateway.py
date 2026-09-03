import pytest

from app.inference_runtime.config import RuntimeConfig
from app.inference_runtime.contracts import (
    Capability,
    CompletionRequest,
    CompletionResult,
    Message,
    ProviderEndpoint,
)
from app.inference_runtime.gateway import HardenedGateway


class Fake:
    async def complete(self, request, endpoint, api_key):
        return CompletionResult("ok", endpoint.provider, endpoint.model, 0.01, 10, 5, 15, 0.001)

    async def health(self):
        return True


@pytest.mark.asyncio
async def test_gateway_end_to_end():
    g = HardenedGateway(RuntimeConfig(default_budget_usd=1))
    ep = ProviderEndpoint("fake", "m", frozenset({Capability.CHAT}), cost_per_1k_input=0.1, cost_per_1k_output=0.2)
    g.register(ep, Fake(), ["k"])
    out = await g.complete(CompletionRequest("m", (Message("user", "hello"),), tenant_id="t"))
    assert out.text == "ok"


@pytest.mark.asyncio
async def test_stream_requires_separate_path():
    g = HardenedGateway(RuntimeConfig(default_budget_usd=1))
    ep = ProviderEndpoint("fake", "m", frozenset({Capability.CHAT}))
    g.register(ep, Fake(), ["k"])
    with pytest.raises(ValueError):
        await g.complete(CompletionRequest("m", (Message("user", "x"),), stream=True))
