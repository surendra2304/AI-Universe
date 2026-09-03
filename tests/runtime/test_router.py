from app.inference_runtime.contracts import Capability, CompletionRequest, Message, ProviderEndpoint
from app.inference_runtime.health import ProviderHealth
from app.inference_runtime.router import CapabilityRouter


def test_capability_and_health_filtering():
    h = ProviderHealth()
    r = CapabilityRouter(h)
    a = ProviderEndpoint("a", "m", frozenset({Capability.CHAT, Capability.JSON}), 1.0)
    b = ProviderEndpoint("b", "m", frozenset({Capability.CHAT}), 1.0)
    r.register(a)
    r.register(b)
    d = r.choose(
        CompletionRequest("m", (Message("user", "x"),), capabilities=frozenset({Capability.CHAT, Capability.JSON}))
    )
    assert d.endpoint.provider == "a"


def test_route_is_deterministic():
    h = ProviderHealth()
    r = CapabilityRouter(h)
    r.register(ProviderEndpoint("b", "m", frozenset({Capability.CHAT})))
    r.register(ProviderEndpoint("a", "m", frozenset({Capability.CHAT})))
    q = CompletionRequest("m", (Message("user", "x"),))
    assert r.choose(q).endpoint.provider == "b"
