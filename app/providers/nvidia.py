"""NVIDIA NIM LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

NVIDIA_DEFAULT_MODEL = "meta/llama-3.1-70b-instruct"

NVIDIA_SUPPORTED_MODELS: List[str] = [
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct"
]


class NvidiaProvider(OpenAICompatibleProvider):
    """NVIDIA NIM inference adapter inheriting from OpenAICompatibleProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = NVIDIA_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.NVIDIA_API_KEY
        super().__init__(
            provider_name="nvidia",
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=key,
            default_model=default_model,
            supported_models=NVIDIA_SUPPORTED_MODELS,
            timeout=timeout
        )
