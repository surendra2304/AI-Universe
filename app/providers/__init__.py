"""Provider factory and registry for AI Universe (8 Active Free Cloud Providers)."""

from typing import Dict, Type
from app.providers.base import BaseLLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.mistral import MistralProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.cohere import CohereProvider
from app.providers.huggingface import HuggingFaceProvider
from app.providers.cloudflare import CloudflareProvider
from app.providers.nvidia import NvidiaProvider

_PROVIDER_MAP: Dict[str, Type[BaseLLMProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "openrouter": OpenRouterProvider,
    "cohere": CohereProvider,
    "huggingface": HuggingFaceProvider,
    "cloudflare": CloudflareProvider,
    "nvidia": NvidiaProvider,
}

_PROVIDER_CACHE: Dict[str, BaseLLMProvider] = {}


def get_provider(name: str = "gemini", **kwargs) -> BaseLLMProvider:
    """Returns a singleton or configured instance of the requested LLM provider."""
    normalized_name = name.lower().strip()
    if normalized_name not in _PROVIDER_MAP:
        raise ValueError(
            f"Unsupported provider '{name}'. Available: {list(_PROVIDER_MAP.keys())}"
        )

    if normalized_name not in _PROVIDER_CACHE or kwargs:
        provider_cls = _PROVIDER_MAP[normalized_name]
        instance = provider_cls(**kwargs)
        if not kwargs:
            _PROVIDER_CACHE[normalized_name] = instance
        return instance

    return _PROVIDER_CACHE[normalized_name]


__all__ = [
    "BaseLLMProvider",
    "GeminiProvider",
    "GroqProvider",
    "MistralProvider",
    "OpenRouterProvider",
    "CohereProvider",
    "HuggingFaceProvider",
    "CloudflareProvider",
    "NvidiaProvider",
    "get_provider",
]
