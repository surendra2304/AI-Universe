"""OpenRouter LLM Provider Adapter."""

from typing import Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Adapter for OpenRouter multi-model aggregation API."""

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
    SUPPORTED_MODELS = [
        "nvidia/nemotron-3.5-lightning:free",
        "liquid/lfm-2.5-2.6b:free",
        "poolside/laguna-s-2.1:free",
        "dots-studio/dots-3-note-preview:free",
        "meta-llama/llama-3.3-70b-instruct"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 60.0
    ) -> None:
        super().__init__(
            provider_name="openrouter",
            base_url=self.BASE_URL,
            api_key=api_key or settings.OPENROUTER_API_KEY,
            default_model=default_model or self.DEFAULT_MODEL,
            supported_models=self.SUPPORTED_MODELS,
            timeout=timeout,
            extra_headers={
                "HTTP-Referer": "https://github.com/surendra2304/AI-Universe",
                "X-Title": "AI Universe"
            }
        )
