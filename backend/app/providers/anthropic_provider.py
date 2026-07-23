"""Anthropic Claude provider."""

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.providers import AIProvider, ChatCompletionResult
from app.providers.openai_provider import _map_provider_error


class AnthropicProvider(AIProvider):
    name = "anthropic"

    async def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatCompletionResult:
        client = Anthropic(api_key=api_key, timeout=get_settings().llm_timeout_seconds)
        messages = []
        for msg in history or []:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_prompt,
                messages=messages,
            )
            content = response.content[0].text if response.content else ""
            tokens = (getattr(response.usage, "input_tokens", 0) or 0) + (
                getattr(response.usage, "output_tokens", 0) or 0
            )
            return ChatCompletionResult(content=content, provider=self.name, model=model, tokens_used=tokens)
        except Exception as exc:
            raise _map_provider_error(self.name, exc) from exc

    async def validate_key(self, api_key: str) -> bool:
        client = Anthropic(api_key=api_key, timeout=20)
        try:
            client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=8,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:
            text = str(exc).lower()
            if "credit" in text or "billing" in text:
                return True  # key authenticates
            return False
