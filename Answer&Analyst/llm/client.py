"""
LLM backend abstraction.

The Analyst and Answer agents never call a vendor SDK directly - they
depend on this interface (Strategy pattern), so swapping OpenAI /
Anthropic / a self-hosted model / a mock for tests never touches agent
code. Register whichever concrete client you need at composition time.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Anything that can turn a prompt into text."""

    @abstractmethod
    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """
    Deterministic stand-in so agents can be unit-tested without any API
    key or network access. Not meant for real answers.
    """

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        return f"[mock-llm response for a {len(prompt)}-char prompt]"


class OpenAILLMClient(LLMClient):
    """Thin adapter around the OpenAI SDK. `pip install openai` to use it."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        from openai import OpenAI  # imported lazily: optional dependency

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class OpenRouterLLMClient(LLMClient):
    """
    Thin adapter around OpenRouter (https://openrouter.ai). OpenRouter
    exposes an OpenAI-compatible /chat/completions endpoint in front of
    many providers, so it's accessed through the `openai` SDK pointed at
    a different base_url - no separate package needed.

    `model` uses OpenRouter's "<provider>/<model>" naming, e.g.
    "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-001".
    See https://openrouter.ai/models for the full list.

    `site_url` / `site_name` are optional attribution headers OpenRouter
    uses for https://openrouter.ai/rankings - safe to leave unset.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        *,
        site_url: str | None = None,
        site_name: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._extra_headers: dict[str, str] = {}
        if site_url:
            self._extra_headers["HTTP-Referer"] = site_url
        if site_name:
            self._extra_headers["X-Title"] = site_name

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        from openai import OpenAI  # imported lazily: optional dependency

        client = OpenAI(api_key=self._api_key, base_url="https://openrouter.ai/api/v1")
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers=self._extra_headers or None,
        )
        return response.choices[0].message.content or ""


class AnthropicLLMClient(LLMClient):
    """Thin adapter around the Anthropic SDK. `pip install anthropic` to use it."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        import anthropic  # imported lazily: optional dependency

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
