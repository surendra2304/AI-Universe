"""Google Gemini provider adapter."""

from app.providers.base import BaseLLMProvider
from typing import Any, Dict


class GeminiProvider(BaseLLMProvider):
    """Adapter for Google Gemini API."""

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Gemini provider implementation pending.")

    async def health(self) -> bool:
        return False
