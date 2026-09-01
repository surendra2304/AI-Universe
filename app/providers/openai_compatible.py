"""Base OpenAI-compatible LLM Provider Adapter."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.providers.base import (
    BaseLLMProvider,
    ProviderCapabilities,
    ProviderRequest,
    ProviderResponse,
    UsageEstimate,
)
from app.utils.logger import logger


class OpenAICompatibleProvider(BaseLLMProvider):
    """Reusable adapter for providers adhering to the OpenAI chat completions REST format."""

    def __init__(
        self,
        provider_name: str,
        base_url: str,
        api_key: str | None,
        default_model: str,
        supported_models: list[str],
        timeout: float = 60.0,
        extra_headers: dict[str, str] | None = None
    ) -> None:
        self._provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.api_keys = [k.strip() for k in (api_key or "").split(",") if k.strip()]
        self._key_index = 0
        self.default_model = default_model
        self.supported_models = supported_models
        self.timeout = timeout
        self.extra_headers = extra_headers or {}

    @property
    def api_key(self) -> str | None:
        if not self.api_keys:
            return None
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return key

    @api_key.setter
    def api_key(self, val: str | None) -> None:
        if val:
            self.api_keys = [k.strip() for k in val.split(",") if k.strip()]
        else:
            self.api_keys = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=self._provider_name,
            supported_models=self.supported_models,
            supports_streaming=True,
            supports_structured_output=True,
            supports_system_instructions=True,
            supports_tool_calling=True,
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

    def _build_payload(self, request: ProviderRequest) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})

        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        model = request.model or self.default_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.response_schema:
            payload["response_format"] = {"type": "json_object"}

        payload.update(request.extra_params)
        return payload

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        headers.update(self.extra_headers)
        return headers

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        active_key = self.api_key
        if not active_key:
            raise ValueError(f"{self._provider_name.upper()}_API_KEY is not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {active_key}"
        }
        headers.update(self.extra_headers)
        payload = self._build_payload(request)
        model = payload["model"]

        start_time = time.perf_counter()
        timeout_config = httpx.Timeout(self.timeout, connect=10.0)
        limits_config = httpx.Limits(max_connections=5, max_keepalive_connections=5)
        try:
            async with httpx.AsyncClient(timeout=timeout_config, limits=limits_config) as client:
                response = await client.post(url, headers=headers, json=payload)
                latency = time.perf_counter() - start_time

                if response.status_code in (429, 503):
                    logger.warning("%s transient error (%d) encountered on model %s; cooling down for 2.0s", self._provider_name, response.status_code, model)
                    await asyncio.sleep(2.0)
                    if response.status_code == 429:
                        raise RuntimeError(f"{self._provider_name.capitalize()} rate limit exceeded (HTTP 429).")
                    else:
                        raise RuntimeError(f"{self._provider_name.capitalize()} service unavailable (HTTP 503): {response.text}")
                elif response.status_code != 200:
                    error_msg = response.text
                    logger.error("%s API error (%d): %s", self._provider_name, response.status_code, error_msg)
                    raise RuntimeError(f"{self._provider_name.capitalize()} API returned HTTP {response.status_code}: {error_msg}")

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    return ProviderResponse(
                        content="",
                        model=model,
                        provider=self._provider_name,
                        latency_seconds=latency,
                        finish_reason="empty",
                        raw_response=data
                    )

                content = choices[0].get("message", {}).get("content", "")
                finish_reason = choices[0].get("finish_reason", "stop")

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

                return ProviderResponse(
                    content=content or "",
                    model=model,
                    provider=self._provider_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_seconds=round(latency, 4),
                    finish_reason=finish_reason,
                    raw_response=data
                )
        except httpx.TimeoutException as exc:
            logger.error("%s request timed out after %.1fs", self._provider_name, self.timeout)
            raise TimeoutError(f"{self._provider_name.capitalize()} API request timed out after {self.timeout}s") from exc
        except httpx.RequestError as exc:
            logger.error("%s network request failure: %s", self._provider_name, type(exc).__name__)
            raise RuntimeError(f"{self._provider_name.capitalize()} network connection error: {type(exc).__name__}") from exc

    async def stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError(f"{self._provider_name.upper()}_API_KEY is not configured.")

        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()
        payload = self._build_payload(request)
        payload["stream"] = True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as stream_resp:
                    if stream_resp.status_code != 200:
                        error_body = await stream_resp.aread()
                        raise RuntimeError(f"{self._provider_name.capitalize()} streaming failed: {error_body.decode('utf-8')}")

                    async for line in stream_resp.aiter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            if raw_data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(raw_data)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content_chunk = delta.get("content", "")
                                    if content_chunk:
                                        yield content_chunk
                            except json.JSONDecodeError:
                                continue
        except httpx.RequestError as exc:
            logger.error("%s streaming connection failure: %s", self._provider_name, type(exc).__name__)
            raise RuntimeError(f"{self._provider_name.capitalize()} streaming connection error: {type(exc).__name__}") from exc

    async def health(self) -> bool:
        if not self.api_key:
            return False
        url = f"{self.base_url}/models"
        headers = self._get_headers()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception as exc:
            logger.warning("%s health probe failed: %s", self._provider_name, str(exc))
            return False
