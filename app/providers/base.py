"""Base LLM Provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for cloud LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate a completion for the given prompt."""
        pass

    @abstractmethod
    async def health(self) -> bool:
        """Check provider connectivity and credential status."""
        pass
