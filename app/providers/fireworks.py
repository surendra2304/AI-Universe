"""Fireworks AI LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

FIREWORKS_DEFAULT_MODEL = "accounts/fireworks/models/llama-v3p1-70b-instruct"

FIREWORKS_SUPPORTED_MODELS: List[str] = [
    "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "accounts/fireworks/models/llama-v3p3-70b-instruct",
    "accounts/fireworks/models/llama-v3p1-8b-instruct",
    "accounts/fireworks/models/mixtral-8x7b-instruct",
    "accounts/fireworks/models/qwen2p5-72b-instruct",
    "accounts/fireworks/models/deepseek-v3"
]


class FireworksProvider(OpenAICompatibleProvider):
    """Fireworks AI inference adapter inheriting from OpenAICompatibleProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = FIREWORKS_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.FIREWORKS_API_KEY
        super().__init__(
            provider_name="fireworks",
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=key,
            default_model=default_model,
            supported_models=FIREWORKS_SUPPORTED_MODELS,
            timeout=timeout
        )
