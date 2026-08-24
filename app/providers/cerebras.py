"""Cerebras LLM Provider Adapter."""

from typing import Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class CerebrasProvider(OpenAICompatibleProvider):
    """Adapter for Cerebras Cloud API."""

    BASE_URL = "https://api.cerebras.ai/v1"
    DEFAULT_MODEL = "llama3.1-70b"
    SUPPORTED_MODELS = [
        "llama3.1-70b",
        "llama3.1-8b"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 60.0
    ) -> None:
        super().__init__(
            provider_name="cerebras",
            base_url=self.BASE_URL,
            api_key=api_key or settings.CEREBRAS_API_KEY,
            default_model=default_model or self.DEFAULT_MODEL,
            supported_models=self.SUPPORTED_MODELS,
            timeout=timeout
        )
