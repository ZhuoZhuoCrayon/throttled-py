"""Fixtures for FastAPI contrib tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest
from fastapi import FastAPI
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.store import MemoryStore
from throttled.constants import RateLimiterType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


@pytest.fixture
def build_app() -> Callable[..., tuple[FastAPI, Limiter]]:
    """Return a factory that produces a fresh ``(FastAPI, Limiter)``
    pair per test. Middleware and exception handler are registered
    automatically.
    """

    def _build(quota: str = "2/s", **limiter_kwargs: Any) -> tuple[FastAPI, Limiter]:
        limiter_kwargs.setdefault("store", MemoryStore())
        limiter: Limiter = Limiter(quota, **limiter_kwargs)
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)
        app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)
        return app, limiter

    return _build


async def asgi_client(
    app: FastAPI,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an HTTPX client bound to the app's ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


ALGORITHMS: list[str] = [
    RateLimiterType.FIXED_WINDOW.value,
    RateLimiterType.SLIDING_WINDOW.value,
    RateLimiterType.TOKEN_BUCKET.value,
    RateLimiterType.LEAKING_BUCKET.value,
    RateLimiterType.GCRA.value,
]
