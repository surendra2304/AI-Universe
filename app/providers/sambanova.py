"""SambaNova Cloud LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

SAMBANOVA_DEFAULT_MODEL = "Meta-Llama-3.3-70B-Instruct"

SAMBANOVA_SUPPORTED_MODELS: List[str] = [
    "Meta-Llama-3.3-70B-Instruct",
    "Meta-Llama-3.1-70B-Instruct",
    "Meta-Llama-3.1-8B-Instruct",
    "Meta-Llama-3.1-405B-Instruct",
    "Qwen2.5-72B-Instruct",
    "DeepSeek-R1-Distill-Llama-70B"
]


class SambaNovaProvider(OpenAICompatibleProvider):
    """SambaNova Cloud inference adapter inheriting from OpenAICompatibleProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = SAMBANOVA_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.SAMBANOVA_API_KEY
        super().__init__(
            provider_name="sambanova",
            base_url="https://api.sambanova.ai/v1",
            api_key=key,
            default_model=default_model,
            supported_models=SAMBANOVA_SUPPORTED_MODELS,
            timeout=timeout
        )
