"""Base LLM Provider interface and data contracts."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderMessage(BaseModel):
    """Message payload for provider requests."""
    role: str = Field(description="Role of the author: system, user, assistant, or tool")
    content: str = Field(description="Textual message content")
    name: Optional[str] = Field(default=None, description="Optional author or agent name")


class ProviderRequest(BaseModel):
    """Standardized request sent to any LLM provider."""
    messages: List[ProviderMessage] = Field(description="List of conversation/debate messages")
    system_instruction: Optional[str] = Field(default=None, description="System-level prompt instructions")
    model: Optional[str] = Field(default=None, description="Target model name override")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="Max output tokens to generate")
    response_schema: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured JSON schema")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific tuning parameters")


class UsageEstimate(BaseModel):
    """Token and cost estimation for a request."""
    estimated_prompt_tokens: int = 0
    estimated_completion_tokens: int = 0
    estimated_total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ProviderCapabilities(BaseModel):
    """Metadata describing provider features and limitations."""
    provider_name: str
    supported_models: List[str]
    supports_streaming: bool = True
    supports_structured_output: bool = True
    supports_system_instructions: bool = True
    supports_tool_calling: bool = True
    max_context_window: int = 128000
    rate_limits: Dict[str, Any] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    """Standardized response from an LLM provider."""
    content: str = Field(description="Generated text content")
    model: str = Field(description="Model identifier that produced the response")
    provider: str = Field(description="Provider name")
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0
    latency_seconds: float = 0.0
    finish_reason: Optional[str] = "stop"
    raw_response: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for cloud LLM provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. gemini, groq, cerebras, mistral, openrouter)."""
        pass

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate a complete response for the given standardized request."""
        pass

    @abstractmethod
    async def stream(self, request: ProviderRequest) -> AsyncIterator[str]:
        """Stream chunks of generated text for the given request."""
        pass

    @abstractmethod
    def estimate_usage(self, request: ProviderRequest) -> UsageEstimate:
        """Estimate token consumption and compute cost before making the API call."""
        pass

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return provider features, supported models, and limits."""
        pass

    @abstractmethod
    async def health(self) -> bool:
        """Check provider connectivity, authentication, and service availability."""
        pass
