from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class LLMError(Exception):
    """Raised when an AI provider request fails."""

    def __init__(self, message: str, provider: str = "", model: str = ""):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    raw: Optional[Any] = None


class LLMProvider(ABC):
    name: str = "base"
    default_model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Run a prompt through the provider and return a unified response."""
