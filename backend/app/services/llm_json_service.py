"""Parse structured JSON from LLM responses."""

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import LLMResponseError
from app.core.llm_router import Intent, get_llm_router

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> dict:
    """Extract JSON object from LLM text, handling markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise LLMResponseError("No JSON object found in LLM response.")

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"Invalid JSON in LLM response: {e}") from e


async def generate_structured(
    user_message: str,
    system_prompt: str,
    intent: Intent,
    response_model: Type[T],
) -> T:
    """Call LLM and validate response against a Pydantic model."""
    router = get_llm_router()
    llm_response = await router.route_and_respond(
        user_message=user_message,
        system_prompt=system_prompt,
        intent=intent,
    )
    data = extract_json(llm_response.content)
    try:
        return response_model.model_validate(data)
    except ValidationError as e:
        raise LLMResponseError(f"Response validation failed: {e}") from e
