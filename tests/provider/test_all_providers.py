"""Unit and mock tests for all 7 non-Gemini provider adapters (Groq, Mistral, OpenRouter, Cohere, HuggingFace, Cloudflare, NVIDIA)."""

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
from app.providers.cloudflare import CloudflareProvider
from app.providers.nvidia import NvidiaProvider


@pytest.mark.parametrize("provider_name,cls,default_model", [
    ("groq", GroqProvider, "llama-3.3-70b-versatile"),
    ("mistral", MistralProvider, "mistral-large-latest"),
    ("openrouter", OpenRouterProvider, "anthropic/claude-3.7-sonnet"),
    ("cohere", CohereProvider, "command-r-plus"),
    ("huggingface", HuggingFaceProvider, "meta-llama/Llama-3.3-70B-Instruct"),
    ("cloudflare", CloudflareProvider, "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
    ("nvidia", NvidiaProvider, "meta/llama-3.1-70b-instruct"),
])
def test_provider_factory_and_capabilities(provider_name, cls, default_model):
    kwargs = {"api_key": "test_key_123"}
    if provider_name == "cloudflare":
        kwargs["account_id"] = "test_account_123"
    provider = get_provider(provider_name, **kwargs)
    assert isinstance(provider, cls)
    assert provider.provider_name == provider_name
    caps = provider.capabilities()
    assert default_model in caps.supported_models
    assert caps.supports_streaming is True


@pytest.mark.parametrize("provider_name", [
    "groq", "mistral", "openrouter", "cohere", "huggingface", "cloudflare", "nvidia"
])
@pytest.mark.asyncio
async def test_openai_compatible_generate(provider_name):
    # Unpatch for unit testing OpenAICompatibleProvider._generate directly
    original_generate = OpenAICompatibleProvider.__dict__.get("generate")
    kwargs = {"api_key": "test_key_mock"}
    if provider_name == "cloudflare":
        kwargs["account_id"] = "test_acc_mock"
    provider = get_provider(provider_name, **kwargs)
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

    # Use original generate with mocked httpx.AsyncClient.post
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
