"""OpenRouter provider adapter."""

from app.providers.base import BaseLLMProvider
from typing import Any, Dict


class OpenRouterProvider(BaseLLMProvider):
    """Adapter for OpenRouter API."""

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("OpenRouter provider implementation pending.")

    async def health(self) -> bool:
        return False
