"""Mistral provider adapter."""

from app.providers.base import BaseLLMProvider
from typing import Any, Dict


class MistralProvider(BaseLLMProvider):
    """Adapter for Mistral API."""

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Mistral provider implementation pending.")

    async def health(self) -> bool:
        return False
