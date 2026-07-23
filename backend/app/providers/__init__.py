"""AI provider adapter registry and interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


SUPPORTED_PROVIDERS = ("openai", "anthropic", "gemini", "groq")

PROVIDER_MODELS: dict[str, list[dict[str, str]]] = {
    "openai": [
        {"id": "gpt-4o-mini", "label": "GPT-4o mini"},
        {"id": "gpt-4o", "label": "GPT-4o"},
    ],
    "anthropic": [
        {"id": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4"},
        {"id": "claude-3-5-haiku-20241022", "label": "Claude 3.5 Haiku"},
    ],
    "gemini": [
        {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash"},
        {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro"},
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B"},
        {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B Instant"},
    ],
}


@dataclass
class ChatCompletionResult:
    content: str
    provider: str
    model: str
    tokens_used: int = 0


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatCompletionResult:
        raise NotImplementedError

    @abstractmethod
    async def validate_key(self, api_key: str) -> bool:
        raise NotImplementedError

    def supported_models(self) -> list[dict[str, str]]:
        return PROVIDER_MODELS.get(self.name, [])


def get_provider(name: str) -> AIProvider:
    from app.providers.anthropic_provider import AnthropicProvider
    from app.providers.gemini_provider import GeminiProvider
    from app.providers.groq_provider import GroqProvider
    from app.providers.openai_provider import OpenAIProvider

    mapping: dict[str, type[AIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "groq": GroqProvider,
    }
    if name not in mapping:
        raise ValueError(f"Unsupported provider: {name}")
    return mapping[name]()


def list_provider_catalog() -> list[dict]:
    return [
        {
            "id": provider,
            "label": provider.title() if provider != "openai" else "OpenAI",
            "models": PROVIDER_MODELS[provider],
        }
        for provider in SUPPORTED_PROVIDERS
    ]
