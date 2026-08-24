"""Together AI LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

TOGETHER_DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

TOGETHER_SUPPORTED_MODELS: List[str] = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "deepseek-ai/DeepSeek-V3",
    "Qwen/Qwen2.5-72B-Instruct-Turbo"
]


class TogetherProvider(OpenAICompatibleProvider):
    """Together AI inference adapter inheriting from OpenAICompatibleProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = TOGETHER_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.TOGETHER_API_KEY
        super().__init__(
            provider_name="together",
            base_url="https://api.together.xyz/v1",
            api_key=key,
            default_model=default_model,
            supported_models=TOGETHER_SUPPORTED_MODELS,
            timeout=timeout
        )
