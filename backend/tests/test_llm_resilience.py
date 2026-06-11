"""LLM timeout/retry behavior tests."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import LLMServiceUnavailable
from app.core.llm_router import LLMRouter


@pytest.mark.asyncio
async def test_execute_with_retry_raises_after_exhausted():
    router = LLMRouter.__new__(LLMRouter)
    router.settings = MagicMock()
    router.settings.llm_timeout_seconds = 1
    router.settings.llm_max_retries = 1

    async def always_fail():
        raise ConnectionError("provider down")

    with pytest.raises(LLMServiceUnavailable, match="unavailable after"):
        await router._execute_with_retry("test_op", always_fail)


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_on_second_attempt():
    router = LLMRouter.__new__(LLMRouter)
    router.settings = MagicMock()
    router.settings.llm_timeout_seconds = 2
    router.settings.llm_max_retries = 2

    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ConnectionError("temporary")
        return "ok"

    result = await router._execute_with_retry("test_op", flaky)
    assert result == "ok"
    assert attempts["count"] == 2
