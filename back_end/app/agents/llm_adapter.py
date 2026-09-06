"""
LLM Client adapter bridging Groq LLM client to the Analyst/Answer Agent interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from app.core.llm import llm_client
from app.config import settings
from app.core.logging import app_logger


class LLMClient(ABC):
    """Abstract interface used by AnalystAgent and AnswerAgent."""

    @abstractmethod
    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        raise NotImplementedError


class GroqLLMClientAdapter(LLMClient):
    """
    Concrete adapter utilizing GroqLLMClient (qwen/qwen3.8-27b).
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.llm_model

    def complete(self, prompt: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str:
        messages = [
            {"role": "user", "content": prompt}
        ]
        return llm_client.generate(
            messages=messages,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens
        )
