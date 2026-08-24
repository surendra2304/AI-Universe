"""Cohere LLM Provider Adapter."""

import time
from typing import AsyncIterator, List, Optional
import httpx

from app.core.config import settings
from app.providers.base import (
    BaseLLMProvider,
    ProviderCapabilities,
    ProviderRequest,
    ProviderResponse,
    UsageEstimate,
)
from app.utils.logger import logger

COHERE_DEFAULT_MODEL = "command-r7b-12-2024"
COHERE_SUPPORTED_MODELS: List[str] = [
    "command-r7b-12-2024",
    "command-r-08-2024",
    "command-light",
    "command"
]


class CohereProvider(BaseLLMProvider):
    """Cohere inference adapter utilizing Cohere's /v1/chat endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = COHERE_DEFAULT_MODEL,
        timeout: float = 60.0
    ) -> None:
        self.api_key = api_key or settings.COHERE_API_KEY
        self.default_model = default_model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "cohere"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="cohere",
            supported_models=COHERE_SUPPORTED_MODELS,
            supports_streaming=True,
            supports_structured_output=True,
            supports_system_instructions=True,
            supports_tool_calling=False,
            max_context_window=128000
        )

    def estimate_usage(self, request: ProviderRequest) -> UsageEstimate:
        total_chars = sum(len(m.content) for m in request.messages)
        if request.system_instruction:
            total_chars += len(request.system_instruction)
        prompt_tokens = max(1, total_chars // 4)
        max_completion = request.max_tokens or 1000
        cost = (prompt_tokens * 0.0000001) + (max_completion * 0.0000004)
        return UsageEstimate(
            estimated_prompt_tokens=prompt_tokens,
            estimated_completion_tokens=max_completion,
            estimated_total_tokens=prompt_tokens + max_completion,
            estimated_cost_usd=round(cost, 6)
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            raise ValueError("COHERE_API_KEY is not configured.")

        url = "https://api.cohere.com/v1/chat"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Build message history for Cohere v1
        chat_history = []
        last_message = ""
        for m in request.messages:
            if m == request.messages[-1] and m.role == "user":
                last_message = m.content
            else:
                role = "USER" if m.role == "user" else "CHATBOT"
                chat_history.append({"role": role, "message": m.content})

        if not last_message and request.messages:
            last_message = request.messages[-1].content

        model = request.model or self.default_model
        payload = {
            "model": model,
            "message": last_message,
            "temperature": request.temperature,
        }
        if request.system_instruction:
            payload["preamble"] = request.system_instruction
        if chat_history:
            payload["chat_history"] = chat_history
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                latency = time.perf_counter() - start_time

                if response.status_code == 429:
                    raise RuntimeError("Cohere rate limit exceeded (HTTP 429).")
                elif response.status_code != 200:
                    raise RuntimeError(f"Cohere API returned HTTP {response.status_code}: {response.text}")

                data = response.json()
                content = data.get("text", "")
                meta = data.get("meta", {}).get("tokens", {})
                prompt_tokens = meta.get("input_tokens", 0)
                completion_tokens = meta.get("output_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens

                return ProviderResponse(
                    content=content.strip(),
                    model=model,
                    provider="cohere",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_seconds=round(latency, 4),
                    finish_reason="stop",
                    raw_response=data
                )
        except Exception as exc:
            logger.error("Cohere request failure: %s", str(exc))
            raise exc

    async def stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        resp = await self.generate(request)
        yield resp.content

    async def health(self) -> bool:
        return bool(self.api_key)
