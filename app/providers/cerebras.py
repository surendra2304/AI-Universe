"""Cerebras provider adapter."""

from app.providers.base import BaseLLMProvider
from typing import Any, Dict


class CerebrasProvider(BaseLLMProvider):
    """Adapter for Cerebras API."""

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("Cerebras provider implementation pending.")

    async def health(self) -> bool:
        return False
