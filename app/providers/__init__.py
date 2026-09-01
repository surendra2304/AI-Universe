"""Provider factory and registry for Inference (7 Verified Free Cloud Providers)."""

from app.providers.base import BaseLLMProvider
from app.providers.cohere import CohereProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.huggingface import HuggingFaceProvider
from app.providers.mistral import MistralProvider
from app.providers.nvidia import NvidiaProvider
from app.providers.openrouter import OpenRouterProvider

_PROVIDER_MAP: dict[str, type[BaseLLMProvider]] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "openrouter": OpenRouterProvider,
    "cohere": CohereProvider,
    "huggingface": HuggingFaceProvider,
    "nvidia": NvidiaProvider,
}

_PROVIDER_CACHE: dict[str, BaseLLMProvider] = {}


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
    "CohereProvider",
    "GeminiProvider",
    "GroqProvider",
    "HuggingFaceProvider",
    "MistralProvider",
    "NvidiaProvider",
    "OpenRouterProvider",
    "get_provider",
]
