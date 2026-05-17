"""Fixtures for FastAPI contrib tests."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from fastapi import FastAPI
from throttled.asyncio import RateLimiterType
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.store import MemoryStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


def setup_app(app: FastAPI) -> None:
    """Register middleware and exception handler on a FastAPI app.

    Helper for tests that build apps directly instead of via build_app.
    """
    app.add_middleware(RateLimitMiddleware)
    app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


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
        setup_app(app)
        return app, limiter

    return _build


@asynccontextmanager
async def asgi_client(
    app: FastAPI,
) -> AsyncIterator[httpx.AsyncClient]:
    """Async context manager yielding an HTTPX client bound to the
    app's ASGI transport.

    Usage::

        async with asgi_client(app) as client:
            await client.get("/x")
    """
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
