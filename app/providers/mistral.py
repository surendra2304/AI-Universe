"""Mistral AI Provider Adapter."""

from typing import Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    """Adapter for Mistral AI API."""

    BASE_URL = "https://api.mistral.ai/v1"
    DEFAULT_MODEL = "mistral-large-latest"
    SUPPORTED_MODELS = [
        "mistral-large-latest",
        "mistral-small-latest",
        "codestral-latest",
        "ministral-8b-latest"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 60.0
    ) -> None:
        super().__init__(
            provider_name="mistral",
            base_url=self.BASE_URL,
            api_key=api_key or settings.MISTRAL_API_KEY,
            default_model=default_model or self.DEFAULT_MODEL,
            supported_models=self.SUPPORTED_MODELS,
            timeout=timeout
        )
