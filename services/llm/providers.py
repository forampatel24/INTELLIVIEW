import time
from typing import Optional

from services.llm.base import LLMError, LLMProvider, LLMResponse, LLMUsage


class GeminiProvider(LLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-pro"

    def __init__(self, api_key: str, model: str = ""):
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not set", provider=self.name)
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self.default_model = model or self.default_model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        model_name = model or self.default_model
        start = time.perf_counter()
        try:
            gen_model = self._genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
            gen_config = self._genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            response = gen_model.generate_content(prompt, generation_config=gen_config)
            latency = (time.perf_counter() - start) * 1000

            usage = LLMUsage()
            try:
                md = response.usage_metadata
                usage.prompt_tokens = md.prompt_token_count or 0
                usage.completion_tokens = md.candidates_token_count or 0
            except Exception:
                pass

            return LLMResponse(
                text=response.text.strip(),
                provider=self.name,
                model=model_name,
                usage=usage,
                latency_ms=latency,
                raw=response,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Gemini request failed: {exc}", provider=self.name, model=model_name) from exc


class OpenAIProvider(LLMProvider):
    name = "openai"
    default_model = "gpt-4o"

    def __init__(self, api_key: str, model: str = ""):
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set", provider=self.name)
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.default_model = model or self.default_model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        model_name = model or self.default_model
        start = time.perf_counter()
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            latency = (time.perf_counter() - start) * 1000
            choice = response.choices[0].message

            usage = LLMUsage(
                prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            )

            return LLMResponse(
                text=(choice.content or "").strip(),
                provider=self.name,
                model=model_name,
                usage=usage,
                latency_ms=latency,
                raw=response,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"OpenAI request failed: {exc}", provider=self.name, model=model_name) from exc


class ClaudeProvider(LLMProvider):
    name = "claude"
    default_model = "claude-sonnet-4"

    def __init__(self, api_key: str, model: str = ""):
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set", provider=self.name)
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self.default_model = model or self.default_model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        model_name = model or self.default_model
        start = time.perf_counter()
        try:
            kwargs = dict(
                model=model_name,
                max_tokens=max_tokens or 4096,
                messages=[{"role": "user", "content": prompt}],
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            if temperature is not None:
                kwargs["temperature"] = temperature

            response = self._client.messages.create(**kwargs)
            latency = (time.perf_counter() - start) * 1000
            text = "".join(block.text for block in response.content if block.type == "text")

            usage = LLMUsage(
                prompt_tokens=getattr(response.usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "output_tokens", 0) or 0,
            )

            return LLMResponse(
                text=text.strip(),
                provider=self.name,
                model=model_name,
                usage=usage,
                latency_ms=latency,
                raw=response,
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"Claude request failed: {exc}", provider=self.name, model=model_name) from exc


class MockProvider(LLMProvider):
    name = "mock"
    default_model = "mock-1"

    def __init__(self, api_key: str = "", model: str = ""):
        self.default_model = model or self.default_model

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        model_name = model or self.default_model
        return LLMResponse(
            text=f"[mock:{model_name}] {prompt[:120]}",
            provider=self.name,
            model=model_name,
        )


PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "mock": MockProvider,
}
