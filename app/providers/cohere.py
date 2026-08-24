"""Cohere LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

COHERE_DEFAULT_MODEL = "command-r-plus"

COHERE_SUPPORTED_MODELS: List[str] = [
    "command-r-plus",
    "command-r",
    "command-light",
    "command"
]


class CohereProvider(OpenAICompatibleProvider):
    """Cohere inference adapter utilizing Cohere's v2 chat / OpenAI compatibility layer."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = COHERE_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.COHERE_API_KEY
        super().__init__(
            provider_name="cohere",
            base_url="https://api.cohere.com/v2",
            api_key=key,
            default_model=default_model,
            supported_models=COHERE_SUPPORTED_MODELS,
            timeout=timeout
        )
