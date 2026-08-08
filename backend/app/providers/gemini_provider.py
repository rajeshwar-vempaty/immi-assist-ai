"""Google Gemini provider."""

from typing import AsyncIterator

import google.generativeai as genai

from app.core.exceptions import AppError
from app.providers import AIProvider, ChatCompletionResult
from app.providers.openai_provider import _map_provider_error


class GeminiProvider(AIProvider):
    name = "gemini"

    def _prompt(self, user_message: str, history: list[dict[str, str]] | None) -> str:
        history_text = ""
        for msg in history or []:
            history_text += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
        return f"{history_text}\nuser: {user_message}" if history_text else user_message

    async def chat(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatCompletionResult:
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(model, system_instruction=system_prompt)
        prompt = self._prompt(user_message, history)
        try:
            response = client.generate_content(prompt)
            content = response.text or ""
            return ChatCompletionResult(content=content, provider=self.name, model=model)
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
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(model, system_instruction=system_prompt)
        prompt = self._prompt(user_message, history)
        try:
            stream = client.generate_content(prompt, stream=True)
            for chunk in stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield text
        except Exception as exc:
            raise _map_provider_error(self.name, exc) from exc

    async def validate_key(self, api_key: str) -> bool:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            model.generate_content("ping")
            return True
        except Exception:
            return False
