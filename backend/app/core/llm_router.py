"""
Multi-LLM Router — Routes queries to the optimal LLM based on intent.

This is the brain of the orchestration layer. It:
1. Classifies user intent using a fast/cheap model
2. Routes to the best LLM for that task
3. Manages fallbacks if a model fails
"""

import asyncio
import json
import logging
import time
from typing import Awaitable, Callable, Optional, TypeVar
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from anthropic import Anthropic
from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMServiceUnavailable
from app.core.prompts import INTENT_CLASSIFIER_PROMPT
from app.observability.metrics import record_llm_call

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    POLICY_QA = "POLICY_QA"
    CHECKLIST = "CHECKLIST"
    TIMELINE = "TIMELINE"
    RFE_HELP = "RFE_HELP"
    GENERAL = "GENERAL"
    CASE_SPECIFIC = "CASE_SPECIFIC"


@dataclass
class ClassifiedIntent:
    intent: Intent
    confidence: float
    sub_topic: str
    visa_type: Optional[str] = None
    requires_lawyer: bool = False


@dataclass
class LLMResponse:
    content: str
    model_used: str
    intent: Intent
    confidence: float
    sources: list[str]
    tokens_used: int = 0


class LLMRouter:
    """
    Routes user queries to the optimal LLM based on classified intent.

    Routing Strategy:
    - POLICY_QA    → Claude (best at nuanced reasoning with citations)
    - CHECKLIST    → Gemini Pro (strong structured JSON output)
    - TIMELINE     → Gemini Pro (data analysis & structured output)
    - RFE_HELP     → Claude (complex legal reasoning)
    - GENERAL      → Gemini Flash (fast, cheap for simple responses)
    - CASE_SPECIFIC → Claude (empathetic, clear about limitations)
    """

    def __init__(self):
        self.settings = get_settings()
        self._init_clients()

    def _init_clients(self):
        """Initialize all LLM clients."""
        # OpenAI client (for embeddings + fallback)
        self.openai_client = OpenAI(api_key=self.settings.openai_api_key)

        # Anthropic client (Claude — reasoning tasks)
        self.anthropic_client = Anthropic(api_key=self.settings.anthropic_api_key)

        # Google Gemini (classification + structured output)
        genai.configure(api_key=self.settings.google_api_key)
        self.gemini_flash = genai.GenerativeModel(self.settings.classifier_model)
        self.gemini_pro = genai.GenerativeModel(self.settings.structured_model)

        logger.info("All LLM clients initialized successfully")

    async def _execute_with_retry(
        self,
        operation_name: str,
        coro_factory: Callable[[], Awaitable[T]],
    ) -> T:
        """Run an async operation with timeout and exponential backoff retries."""
        last_error: Exception | None = None
        max_attempts = self.settings.llm_max_retries + 1

        for attempt in range(max_attempts):
            try:
                return await asyncio.wait_for(
                    coro_factory(),
                    timeout=self.settings.llm_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning(f"{operation_name} timed out (attempt {attempt + 1}/{max_attempts})")
            except Exception as exc:
                last_error = exc
                logger.warning(f"{operation_name} failed (attempt {attempt + 1}/{max_attempts}): {exc}")

            if attempt < max_attempts - 1:
                await asyncio.sleep(2**attempt)

        raise LLMServiceUnavailable(
            f"{operation_name} unavailable after {max_attempts} attempts: {last_error}"
        )

    # ----- Intent Classification -----

    async def classify_intent(self, user_message: str) -> ClassifiedIntent:
        """
        Classify user intent using Gemini Flash (fast & cheap).
        Falls back to keyword-based classification if LLM fails.
        """
        try:

            def _classify_sync() -> ClassifiedIntent:
                response = self.gemini_flash.generate_content(
                    f"{INTENT_CLASSIFIER_PROMPT}\n\nUser message: {user_message}"
                )
                result = json.loads(
                    response.text.strip().removeprefix("```json").removesuffix("```").strip()
                )
                return ClassifiedIntent(
                    intent=Intent(result["intent"]),
                    confidence=result.get("confidence", 0.8),
                    sub_topic=result.get("sub_topic", ""),
                    visa_type=result.get("visa_type"),
                    requires_lawyer=result.get("requires_lawyer", False),
                )

            return await self._execute_with_retry(
                "intent_classification",
                lambda: asyncio.to_thread(_classify_sync),
            )
        except LLMServiceUnavailable as e:
            logger.warning(f"LLM classification failed, using fallback: {e}")
            return self._fallback_classify(user_message)

    def _fallback_classify(self, message: str) -> ClassifiedIntent:
        """Keyword-based fallback classifier."""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["rfe", "request for evidence", "denial", "noid"]):
            return ClassifiedIntent(Intent.RFE_HELP, 0.7, "RFE related")
        elif any(kw in message_lower for kw in ["documents", "checklist", "what do i need", "paperwork", "required"]):
            return ClassifiedIntent(Intent.CHECKLIST, 0.7, "Document checklist")
        elif any(kw in message_lower for kw in ["how long", "processing time", "timeline", "wait", "when will"]):
            return ClassifiedIntent(Intent.TIMELINE, 0.7, "Processing timeline")
        elif any(kw in message_lower for kw in ["my case", "my application", "my receipt"]):
            return ClassifiedIntent(Intent.CASE_SPECIFIC, 0.6, "Case specific")
        elif any(kw in message_lower for kw in ["hello", "hi", "hey", "thanks", "thank you"]):
            return ClassifiedIntent(Intent.GENERAL, 0.9, "Greeting")
        else:
            return ClassifiedIntent(Intent.POLICY_QA, 0.6, "General immigration question")

    # ----- LLM Calls -----

    async def call_claude(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Claude for complex reasoning tasks."""

        def _sync() -> str:
            response = self.anthropic_client.messages.create(
                model=self.settings.reasoning_model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text

        return await self._execute_with_retry("claude", lambda: asyncio.to_thread(_sync))

    async def call_gemini(self, prompt: str, structured: bool = False) -> str:
        """Call Google Gemini for structured output or fast responses."""

        def _sync() -> str:
            model = self.gemini_pro if structured else self.gemini_flash
            response = model.generate_content(prompt)
            return response.text

        return await self._execute_with_retry("gemini", lambda: asyncio.to_thread(_sync))

    async def call_openai(self, system_prompt: str, user_message: str) -> str:
        """Call OpenAI as fallback."""

        def _sync() -> str:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=2048,
            )
            return response.choices[0].message.content

        return await self._execute_with_retry("openai", lambda: asyncio.to_thread(_sync))

    # ----- Routing Logic -----

    async def route_and_respond(
        self,
        user_message: str,
        system_prompt: str,
        intent: Intent,
    ) -> LLMResponse:
        """
        Route to the optimal LLM based on intent, with fallback chain.

        Routing:
            POLICY_QA / RFE_HELP / CASE_SPECIFIC → Claude → OpenAI → Gemini
            CHECKLIST / TIMELINE                  → Gemini → OpenAI → Claude
            GENERAL                               → Gemini Flash → OpenAI
        """
        fallback_chains = {
            Intent.POLICY_QA: [
                ("claude", self.settings.reasoning_model),
                ("openai", "gpt-4o-mini"),
                ("gemini", self.settings.structured_model),
            ],
            Intent.RFE_HELP: [
                ("claude", self.settings.reasoning_model),
                ("openai", "gpt-4o-mini"),
            ],
            Intent.CASE_SPECIFIC: [
                ("claude", self.settings.reasoning_model),
                ("openai", "gpt-4o-mini"),
            ],
            Intent.CHECKLIST: [
                ("gemini", self.settings.structured_model),
                ("openai", "gpt-4o-mini"),
                ("claude", self.settings.reasoning_model),
            ],
            Intent.TIMELINE: [
                ("gemini", self.settings.structured_model),
                ("openai", "gpt-4o-mini"),
            ],
            Intent.GENERAL: [
                ("gemini", self.settings.classifier_model),
                ("openai", "gpt-4o-mini"),
            ],
        }

        chain = fallback_chains.get(intent, fallback_chains[Intent.GENERAL])

        for provider, model_name in chain:
            start = time.perf_counter()
            try:
                if provider == "claude":
                    content = await self.call_claude(system_prompt, user_message)
                elif provider == "gemini":
                    content = await self.call_gemini(f"{system_prompt}\n\nUser: {user_message}")
                elif provider == "openai":
                    content = await self.call_openai(system_prompt, user_message)
                else:
                    continue

                record_llm_call(
                    provider=provider,
                    intent=intent.value,
                    status="success",
                    duration=time.perf_counter() - start,
                )
                logger.info(f"Successfully routed to {provider} ({model_name}) for {intent}")
                return LLMResponse(
                    content=content,
                    model_used=model_name,
                    intent=intent,
                    confidence=1.0,
                    sources=[],
                )

            except LLMServiceUnavailable as e:
                record_llm_call(
                    provider=provider,
                    intent=intent.value,
                    status="error",
                    duration=time.perf_counter() - start,
                )
                logger.warning(f"{provider} failed for {intent}: {e}. Trying fallback...")
                continue

        raise LLMServiceUnavailable(
            f"All LLM providers failed for intent {intent.value}."
        )


# Singleton instance
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create the singleton LLM router."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
