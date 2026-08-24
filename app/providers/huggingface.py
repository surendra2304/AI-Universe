"""HuggingFace Inference API LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

HUGGINGFACE_DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

HUGGINGFACE_SUPPORTED_MODELS: List[str] = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "Qwen/Qwen2.5-72B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
]


class HuggingFaceProvider(OpenAICompatibleProvider):
    """HuggingFace Serverless Inference adapter via OpenAI compatible v1 route."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = HUGGINGFACE_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.HUGGINGFACE_API_KEY
        super().__init__(
            provider_name="huggingface",
            base_url="https://api-inference.huggingface.co/v1",
            api_key=key,
            default_model=default_model,
            supported_models=HUGGINGFACE_SUPPORTED_MODELS,
            timeout=timeout
        )
