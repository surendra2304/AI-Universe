"""DeepSeek LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"

DEEPSEEK_SUPPORTED_MODELS: List[str] = [
    "deepseek-chat",
    "deepseek-reasoner"
]


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek inference adapter inheriting from OpenAICompatibleProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = DEEPSEEK_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.DEEPSEEK_API_KEY
        super().__init__(
            provider_name="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key=key,
            default_model=default_model,
            supported_models=DEEPSEEK_SUPPORTED_MODELS,
            timeout=timeout
        )
