from functools import lru_cache
from typing import Optional

from services.llm.base import LLMError, LLMProvider, LLMResponse
from services.llm.providers import PROVIDER_CLASSES
from utils.config import settings

TASKS = (
    "resume_analysis",
    "question_generation",
    "answer_evaluation",
    "behavior_analysis",
    "feedback_generation",
    "report_generation",
)


class LLMRouter:
    """Routes AI tasks to the configured provider with a unified response format."""

    def __init__(self, provider_config: Optional[dict[str, str]] = None):
        self._provider_config = provider_config or settings.task_providers
        self._instances: dict[str, LLMProvider] = {}

    def provider_for(self, task: str) -> LLMProvider:
        if task not in TASKS:
            raise LLMError(f"Unknown AI task: {task!r}")
        if task not in self._instances:
            self._instances[task] = self._build(task)
        return self._instances[task]

    def _build(self, task: str) -> LLMProvider:
        provider_name = self._provider_config.get(task, settings.default_ai_provider).lower()
        cls = PROVIDER_CLASSES.get(provider_name)
        if cls is None:
            raise LLMError(f"Unsupported provider: {provider_name!r} for task {task!r}")
        if cls.__name__ == "MockProvider":
            return cls()
        if provider_name == "gemini":
            return cls(api_key=settings.gemini_api_key, model=settings.gemini_model)
        if provider_name == "openai":
            return cls(api_key=settings.openai_api_key, model=settings.openai_model)
        if provider_name == "claude":
            return cls(api_key=settings.anthropic_api_key, model=settings.anthropic_model)
        raise LLMError(f"Unsupported provider: {provider_name!r} for task {task!r}")

    def generate(
        self,
        task: str,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        provider = self.provider_for(task)
        return provider.generate(
            prompt,
            system_prompt=system_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )


@lru_cache
def get_router() -> LLMRouter:
    return LLMRouter()


router = get_router()
