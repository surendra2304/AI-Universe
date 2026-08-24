"""Cloudflare Workers AI LLM Provider Adapter."""

from typing import List, Optional
from app.core.config import settings
from app.providers.openai_compatible import OpenAICompatibleProvider

CLOUDFLARE_DEFAULT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

CLOUDFLARE_SUPPORTED_MODELS: List[str] = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-3.1-70b-instruct",
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/mistral/mistral-7b-instruct-v0.1",
    "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
]


class CloudflareProvider(OpenAICompatibleProvider):
    """Cloudflare Workers AI inference adapter via Cloudflare's OpenAI-compatible endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        default_model: str = CLOUDFLARE_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        key = api_key or settings.CLOUDFLARE_API_KEY
        acc_id = account_id or settings.CLOUDFLARE_ACCOUNT_ID or ""
        base_url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/ai/v1"
        super().__init__(
            provider_name="cloudflare",
            base_url=base_url,
            api_key=key,
            default_model=default_model,
            supported_models=CLOUDFLARE_SUPPORTED_MODELS,
            timeout=timeout
        )
