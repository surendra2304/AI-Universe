"""Comprehensive unit and integration tests for LiteLLM Provider Adapter and ModelGateway integration."""

import sys
import types
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.providers.base import ProviderMessage, ProviderRequest
from app.providers.errors import RateLimitError
from app.providers.gateway_litellm import (
    execute_via_litellm,
    litellm_enabled,
    resolve_model,
    sanitize_litellm_params,
)
from app.providers.litellm_adapter import LiteLLMProvider


class MockUsage:
    prompt_tokens = 15
    completion_tokens = 25
    total_tokens = 40


class MockMessage:
    content = "Consensus verified: Event-driven architecture with WAL database."


class MockChoice:
    message = MockMessage()
    finish_reason = "stop"


class MockLiteLLMResponse:
    model = "openai/gpt-4o-mini"
    choices = [MockChoice()]
    usage = MockUsage()

    def model_dump(self):
        return {"model": self.model, "usage": {"total_tokens": 40}}


@pytest.mark.asyncio
async def test_litellm_adapter_maps_response_and_system_prompt(monkeypatch):
    """Verify request, system prompt, tokens, and finish reason mapping."""
    captured_kwargs = {}

    async def fake_acompletion(**kwargs):
        captured_kwargs.update(kwargs)
        return MockLiteLLMResponse()

    # Create fake litellm module
    fake_module = types.ModuleType("litellm")
    fake_module.acompletion = fake_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    provider = LiteLLMProvider(api_key="mock_secret_key")
    req = ProviderRequest(
        model="openai/gpt-4o-mini",
        system_instruction="Act as principal distributed systems architect.",
        messages=[
            ProviderMessage(role="user", content="Design durable storage pipeline.", name="architect")
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    resp = await provider.generate(req)

    assert captured_kwargs["model"] == "openai/gpt-4o-mini"
    assert captured_kwargs["messages"][0] == {"role": "system", "content": "Act as principal distributed systems architect."}
    assert captured_kwargs["messages"][1]["role"] == "user"
    assert captured_kwargs["messages"][1]["name"] == "architect"
    assert captured_kwargs["temperature"] == 0.3
    assert captured_kwargs["max_tokens"] == 2048
    assert captured_kwargs["api_key"] == "mock_secret_key"

    assert resp.content == "Consensus verified: Event-driven architecture with WAL database."
    assert resp.total_tokens == 40
    assert resp.prompt_tokens == 15
    assert resp.completion_tokens == 25
    assert resp.finish_reason == "stop"
    assert resp.provider == "litellm"


@pytest.mark.asyncio
async def test_requires_model():
    """Verify ValueError is raised when request.model is None."""
    provider = LiteLLMProvider()
    with pytest.raises(ValueError, match="requires ProviderRequest.model"):
        await provider.generate(
            ProviderRequest(
                model=None,
                messages=[ProviderMessage(role="user", content="Hi")],
            )
        )


@pytest.mark.asyncio
async def test_structured_output_schema_mapping(monkeypatch):
    """Verify response_schema is mapped to LiteLLM response_format json_schema."""
    captured_kwargs = {}

    async def fake_acompletion(**kwargs):
        captured_kwargs.update(kwargs)
        return MockLiteLLMResponse()

    fake_module = types.ModuleType("litellm")
    fake_module.acompletion = fake_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    schema = {
        "type": "object",
        "properties": {"verdict": {"type": "string"}},
        "required": ["verdict"]
    }
    provider = LiteLLMProvider()
    req = ProviderRequest(
        model="gemini/gemini-2.5-flash",
        messages=[ProviderMessage(role="user", content="Verify claim")],
        response_schema=schema,
    )
    await provider.generate(req)

    assert "response_format" in captured_kwargs
    rf = captured_kwargs["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == schema
    assert rf["json_schema"]["strict"] is True


@pytest.mark.asyncio
async def test_litellm_streaming(monkeypatch):
    """Verify asynchronous streaming generator yields individual chunks."""
    class MockDelta:
        def __init__(self, content):
            self.content = content

    class MockStreamChoice:
        def __init__(self, content):
            self.delta = MockDelta(content)

    class MockChunk:
        def __init__(self, content):
            self.choices = [MockStreamChoice(content)]

    async def fake_stream_generator():
        for token in ["Chunk 1 ", "Chunk 2 ", "Chunk 3"]:
            yield MockChunk(token)

    async def fake_acompletion(**kwargs):
        assert kwargs.get("stream") is True
        return fake_stream_generator()

    fake_module = types.ModuleType("litellm")
    fake_module.acompletion = fake_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    provider = LiteLLMProvider()
    req = ProviderRequest(
        model="groq/llama-3.3-70b-versatile",
        messages=[ProviderMessage(role="user", content="Stream tokens")],
    )

    chunks = []
    async for chunk in provider.stream(req):
        chunks.append(chunk)

    assert chunks == ["Chunk 1 ", "Chunk 2 ", "Chunk 3"]


def test_model_alias_resolution():
    """Verify model alias resolution from settings and custom JSON."""
    aliases = '{"fast": "groq/llama-3.3-70b-versatile", "reasoning": "openrouter/deepseek/deepseek-r1"}'
    assert resolve_model("fast", aliases) == "groq/llama-3.3-70b-versatile"
    assert resolve_model("reasoning", aliases) == "openrouter/deepseek/deepseek-r1"
    assert resolve_model("openai/gpt-4o", aliases) == "openai/gpt-4o"


def test_parameter_sanitization():
    """Verify internal orchestrator control fields are not leaked to LiteLLM."""
    extra = {
        "task_id": "task_123",
        "agent_id": "researcher",
        "routing_reason": "explicit",
        "custom_param": "allowed_value",
    }
    sanitized = sanitize_litellm_params(extra)
    assert "task_id" not in sanitized
    assert "agent_id" not in sanitized
    assert "routing_reason" not in sanitized
    assert sanitized.get("custom_param") == "allowed_value"


@pytest.mark.asyncio
async def test_litellm_disabled_behavior(monkeypatch):
    """Verify execute_via_litellm raises RuntimeError when disabled in settings."""
    monkeypatch.setattr(settings, "INFERENCE_LITELLM_ENABLED", False)
    assert litellm_enabled() is False

    req = ProviderRequest(
        model="openai/gpt-4o-mini",
        messages=[ProviderMessage(role="user", content="Test")],
    )
    with pytest.raises(RuntimeError, match="LiteLLM integration is disabled"):
        await execute_via_litellm(req)


@pytest.mark.asyncio
async def test_litellm_uninstalled_behavior(monkeypatch):
    """Verify clear RuntimeError is raised when the litellm package is missing."""
    monkeypatch.setitem(sys.modules, "litellm", None)

    provider = LiteLLMProvider()
    req = ProviderRequest(
        model="openai/gpt-4o-mini",
        messages=[ProviderMessage(role="user", content="Test")],
    )
    with pytest.raises(RuntimeError, match="not installed"):
        await provider.generate(req)


@pytest.mark.asyncio
async def test_litellm_error_normalization(monkeypatch):
    """Verify raw LiteLLM errors are normalized into typed GatewayError hierarchy."""
    async def fake_failing_acompletion(**kwargs):
        raise Exception("429 RateLimitError: Token limit exceeded")

    fake_module = types.ModuleType("litellm")
    fake_module.acompletion = fake_failing_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    provider = LiteLLMProvider()
    req = ProviderRequest(
        model="openai/gpt-4o-mini",
        messages=[ProviderMessage(role="user", content="Test")],
    )
    with pytest.raises(RateLimitError) as exc_info:
        await provider.generate(req)

    assert exc_info.value.is_retryable() is True
    assert exc_info.value.provider == "litellm"


@pytest.mark.asyncio
async def test_gateway_dynamic_fallback_to_litellm(monkeypatch):
    """Verify ModelGateway falls back to LiteLLM with complete fallback provenance when primary fails."""
    monkeypatch.setattr(settings, "INFERENCE_LITELLM_ENABLED", True)
    monkeypatch.setattr(settings, "INFERENCE_LITELLM_FALLBACK_ENABLED", True)

    async def fake_acompletion(**kwargs):
        return MockLiteLLMResponse()

    fake_module = types.ModuleType("litellm")
    fake_module.acompletion = fake_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake_module)

    from app.providers.gateway import model_gateway

    req = ProviderRequest(
        model="gemini-3.7-flash",
        messages=[ProviderMessage(role="user", content="Analyze trade-offs")],
    )

    # Force primary provider to fail and OpenRouter/Matrix to fail so it reaches LiteLLM fallback
    with patch("app.providers.get_provider") as mock_get_prov:
        failing_prov = AsyncMock()
        failing_prov.generate.side_effect = Exception("503 Service Unavailable")
        mock_get_prov.return_value = failing_prov

        resp = await model_gateway._execute_dynamic_fallback(
            failed_provider="gemini",
            request=req,
            capability="reasoning",
            stage_name="analysis",
            last_error=Exception("503 Service Unavailable")
        )

        assert resp.raw_response is not None
        assert "fallback_provenance" in resp.raw_response
        prov = resp.raw_response["fallback_provenance"]
        assert prov["requested_provider"] == "gemini"
        assert prov["actual_provider"] == "litellm"
        assert prov["capability"] == "reasoning"
