"""Groq provider adapter."""

from app.providers.base import BaseLLMProvider
from typing import Any, Dict


class GroqProvider(BaseLLMProvider):
    """Adapter for Groq API."""

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Groq provider implementation pending.")

    async def health(self) -> bool:
        return False
