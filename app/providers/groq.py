"""Groq LLM Provider Adapter."""

from typing import Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Adapter for Groq cloud API."""

    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "openai/gpt-oss-120b"
    SUPPORTED_MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "groq/compound",
        "groq/compound-mini"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 60.0
    ) -> None:
        super().__init__(
            provider_name="groq",
            base_url=self.BASE_URL,
            api_key=api_key or settings.GROQ_API_KEY,
            default_model=default_model or self.DEFAULT_MODEL,
            supported_models=self.SUPPORTED_MODELS,
            timeout=timeout
        )
