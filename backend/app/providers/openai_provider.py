"""OpenAI chat provider."""

from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.providers import AIProvider, ChatCompletionResult


class OpenAIProvider(AIProvider):
    name = "openai"

    async def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatCompletionResult:
        client = OpenAI(api_key=api_key, timeout=get_settings().llm_timeout_seconds)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history or []:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})
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

    async def validate_key(self, api_key: str) -> bool:
        client = OpenAI(api_key=api_key, timeout=20)
        try:
            client.models.list()
            return True
        except Exception:
            return False


def _map_provider_error(provider: str, exc: Exception) -> AppError:
    text = str(exc).lower()
    if "rate" in text or "429" in text:
        return AppError(f"{provider} rate limit exceeded. Try again later.", status_code=429)
    if "auth" in text or "invalid" in text or "401" in text or "403" in text:
        return AppError(
            f"{provider} API key is invalid or revoked. Update it in Settings.",
            status_code=400,
        )
    if "quota" in text or "billing" in text or "balance" in text:
        return AppError(f"{provider} quota/billing issue. Check your provider account.", status_code=402)
    if "timeout" in text:
        return AppError(f"{provider} request timed out.", status_code=504)
    return AppError(f"{provider} provider error. Please try again.", status_code=502)
