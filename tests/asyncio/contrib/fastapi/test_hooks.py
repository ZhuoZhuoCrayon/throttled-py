"""Hook integration tests for FastAPI contrib.

Verifies that hooks passed to ``Limiter`` reach the underlying
``Throttled`` and execute on every request, including an ``OTelHook``
used in the FastAPI path so metrics recording attributes flow through.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi import (
    FastAPI,
    Request,  # noqa: TCH002 (runtime use: FastAPI signature inspection)
)
from throttled.asyncio.contrib.fastapi import Limiter
from throttled.asyncio.contrib.otel import OTelHook
from throttled.asyncio.hooks import Hook
from throttled.asyncio.store import MemoryStore

from .conftest import asgi_client, setup_app

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from throttled.asyncio.rate_limiter import RateLimitResult
    from throttled.hooks import HookContext

EXPECTED_CALL_COUNT = 2


@pytest.fixture
def mock_meter() -> MagicMock:
    """Mock meter whose create_counter/create_histogram return mocks."""
    meter: MagicMock = MagicMock(name="Meter")
    meter.create_counter.return_value = MagicMock(name="Counter")
    meter.create_histogram.return_value = MagicMock(name="Histogram")
    return meter


class _CountingHook(Hook):
    """Test hook that records every key it sees."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def on_limit(
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context: HookContext,
    ) -> RateLimitResult:
        self.calls.append(context.key)
        return await call_next()


@pytest.mark.asyncio
class TestHooksPassThrough:
    @classmethod
    async def test_hooks__pass_through_to_throttled(cls) -> None:
        """Hooks passed to ``Limiter`` reach the underlying ``Throttled``
        and execute on every rate-limit check."""
        hook = _CountingHook()
        limiter = Limiter("100/m", store=MemoryStore(), hooks=[hook])
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        expected_calls = 3
        async with asgi_client(app) as client:
            for _ in range(expected_calls):
                await client.get("/x")

        assert len(hook.calls) == expected_calls
        assert all("GET" in key for key in hook.calls)


@pytest.mark.asyncio
class TestOTelHookIntegration:
    @classmethod
    async def test_otel_hook__records_allowed_and_denied_via_fastapi(
        cls, mock_meter: MagicMock
    ) -> None:
        """OTelHook installed on the Limiter records one counter/histogram
        call per request when driven through a FastAPI route, capturing
        allowed and denied results with expected attributes."""
        hook = OTelHook(mock_meter)
        counter: MagicMock = mock_meter.create_counter.return_value
        histogram: MagicMock = mock_meter.create_histogram.return_value

        limiter = Limiter("1/s", store=MemoryStore(), hooks=[hook])
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async with asgi_client(app) as client:
            await client.get("/x")  # allowed
            await client.get("/x")  # denied (1/s exhausted)

        # Counter and histogram each recorded once per request.
        assert counter.add.call_count == EXPECTED_CALL_COUNT
        assert histogram.record.call_count == EXPECTED_CALL_COUNT

        allowed_cost, allowed_attrs = counter.add.call_args_list[0].args
        denied_cost, denied_attrs = counter.add.call_args_list[1].args

        assert allowed_cost == 1
        assert allowed_attrs["result"] == "allowed"
        assert allowed_attrs["algorithm"] == "fixed_window"
        assert allowed_attrs["store_type"] == "memory"
        assert "GET" in allowed_attrs["key"]

        assert denied_cost == 1
        assert denied_attrs["result"] == "denied"
        assert denied_attrs["algorithm"] == "fixed_window"
        assert denied_attrs["store_type"] == "memory"
        assert allowed_attrs["key"] == denied_attrs["key"]
