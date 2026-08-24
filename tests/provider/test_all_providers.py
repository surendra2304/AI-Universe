"""Unit and mock tests for all 6 non-Gemini provider adapters (Groq, Mistral, OpenRouter, Cohere, HuggingFace, NVIDIA)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers import get_provider
from app.providers.base import ProviderMessage, ProviderRequest
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.groq import GroqProvider
from app.providers.mistral import MistralProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.cohere import CohereProvider
from app.providers.huggingface import HuggingFaceProvider
from app.providers.nvidia import NvidiaProvider


@pytest.mark.parametrize("provider_name,cls,default_model", [
    ("groq", GroqProvider, "openai/gpt-oss-120b"),
    ("mistral", MistralProvider, "mistral-large-latest"),
    ("openrouter", OpenRouterProvider, "anthropic/claude-3.7-sonnet"),
    ("cohere", CohereProvider, "command-r7b-12-2024"),
    ("huggingface", HuggingFaceProvider, "meta-llama/llama-3.1-8b-instruct"),
    ("nvidia", NvidiaProvider, "meta/llama-3.1-70b-instruct"),
])
def test_provider_factory_and_capabilities(provider_name, cls, default_model):
    provider = get_provider(provider_name, api_key="test_key_123")
    assert isinstance(provider, cls)
    assert provider.provider_name == provider_name
    caps = provider.capabilities()
    assert default_model in caps.supported_models
    assert caps.supports_streaming is True


@pytest.mark.parametrize("provider_name", [
    "groq", "mistral", "openrouter", "huggingface", "nvidia"
])
@pytest.mark.asyncio
async def test_openai_compatible_generate(provider_name):
    original_generate = OpenAICompatibleProvider.__dict__.get("generate")
    provider = get_provider(provider_name, api_key="test_key_mock")
    req = ProviderRequest(
        messages=[ProviderMessage(role="user", content="Hello world")]
    )

    mock_resp_data = {
        "choices": [
            {
                "message": {"content": f"Direct response from {provider_name}"},
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }

    with patch.object(OpenAICompatibleProvider, "generate", original_generate):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_resp_data
            mock_post.return_value = mock_resp

            result = await provider.generate(req)
            assert result.content == f"Direct response from {provider_name}"
            assert result.provider == provider_name
            assert result.total_tokens == 15


@pytest.mark.asyncio
async def test_cohere_generate():
    provider = get_provider("cohere", api_key="test_key_mock")
    req = ProviderRequest(
        messages=[ProviderMessage(role="user", content="Hello world")]
    )

    mock_resp_data = {
        "text": "Direct response from cohere",
        "meta": {
            "tokens": {
                "input_tokens": 10,
                "output_tokens": 5
            }
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_resp_data
        mock_post.return_value = mock_resp

        result = await provider.generate(req)
        assert result.content == "Direct response from cohere"
        assert result.provider == "cohere"
        assert result.total_tokens == 15
