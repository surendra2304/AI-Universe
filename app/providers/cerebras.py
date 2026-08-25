"""Cerebras Cloud LLM provider implementation."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class CerebrasProvider(OpenAICompatibleProvider):
    """Provider adapter for Cerebras high-speed inference API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.cerebras.ai/v1",
        default_model: str = "llama3.1-8b",
        timeout: float = 30.0
    ) -> None:
        key = api_key or settings.CEREBRAS_API_KEY
        super().__init__(
            provider_name="cerebras",
            api_key=key,
            base_url=base_url,
            default_model=default_model,
            timeout=timeout
        )

    def supported_models(self) -> List[str]:
        return [
            "llama3.1-8b",
            "llama3.1-70b",
            "llama-3.3-70b"
        ]
