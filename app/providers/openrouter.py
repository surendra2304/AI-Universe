"""OpenRouter LLM Provider Adapter."""

from typing import Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Adapter for OpenRouter multi-model aggregation API."""

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"
    SUPPORTED_MODELS = [
        "anthropic/claude-3.7-sonnet",
        "openai/gpt-4o",
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-r1",
        "google/gemini-2.5-flash"
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
