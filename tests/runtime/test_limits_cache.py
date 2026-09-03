from app.inference_runtime.contracts import CompletionRequest, Message
from app.inference_runtime.request_limits import RequestLimits


def test_request_limits_allow_small():
    RequestLimits().validate(CompletionRequest("m", (Message("user", "x"),)))


def test_cache_policy_stream_denied():
    from app.inference_runtime.cache_policy import CachePolicy

    assert not CachePolicy().decide(CompletionRequest("m", (Message("user", "x"),), stream=True)).allowed
