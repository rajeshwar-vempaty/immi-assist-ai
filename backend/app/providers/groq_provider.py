"""Groq provider (OpenAI-compatible API)."""

from typing import AsyncIterator

from openai import OpenAI

from app.core.config import get_settings
from app.providers import AIProvider, ChatCompletionResult
from app.providers.openai_provider import _map_provider_error


class GroqProvider(AIProvider):
    name = "groq"

    def _client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=get_settings().llm_timeout_seconds,
        )

    def _messages(
        self,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history or []:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatCompletionResult:
        client = self._client(api_key)
        messages = self._messages(system_prompt, user_message, history)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2048,
            )
            content = response.choices[0].message.content or ""
            tokens = getattr(response.usage, "total_tokens", 0) or 0
            return ChatCompletionResult(content=content, provider=self.name, model=model, tokens_used=tokens)
        except Exception as exc:
            raise _map_provider_error(self.name, exc) from exc

    async def chat_stream(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        client = self._client(api_key)
        messages = self._messages(system_prompt, user_message, history)
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2048,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:
            raise _map_provider_error(self.name, exc) from exc

    async def validate_key(self, api_key: str) -> bool:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1", timeout=20)
        try:
            client.models.list()
            return True
        except Exception:
            return False
