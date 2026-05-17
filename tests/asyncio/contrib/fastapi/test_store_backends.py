"""Store backend integration tests for FastAPI contrib.

Verifies that the contrib forwards user-provided store backends
(Memory, Redis) to the underlying ``Throttled`` and that rate-limit
behavior is consistent across backends.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import (
    FastAPI,
    Request,  # noqa: TCH002 (runtime use: FastAPI signature inspection)
)
from throttled.asyncio.contrib.fastapi import Limiter

from .conftest import asgi_client, setup_app

if TYPE_CHECKING:
    from throttled.asyncio.store import BaseStore, RedisStore


@pytest.mark.asyncio
class TestStoreBackends:
    @classmethod
    async def test_backend__below_quota__allows_requests(
        cls, store: BaseStore[Any]
    ) -> None:
        """Both Memory and Redis backends allow under-quota requests."""
        limiter = Limiter("5/s", store=store)
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async with asgi_client(app) as client:
            r1 = await client.get("/x")
            r2 = await client.get("/x")
        assert r1.status_code == HTTPStatus.OK
        assert r2.status_code == HTTPStatus.OK
        assert r1.headers["RateLimit-Remaining"] == "4"
        assert r2.headers["RateLimit-Remaining"] == "3"

    @classmethod
    async def test_backend__quota_exhausted__returns_429(
        cls, store: BaseStore[Any]
    ) -> None:
        """Both backends produce 429 with IETF headers on exhaustion."""
        limiter = Limiter("1/s", store=store)
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async with asgi_client(app) as client:
            ok = await client.get("/x")
            limited = await client.get("/x")

        assert ok.status_code == HTTPStatus.OK
        assert limited.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert limited.headers["RateLimit-Limit"] == "1"
        assert limited.headers["RateLimit-Remaining"] == "0"
        assert "Retry-After" in limited.headers


@pytest.mark.asyncio
class TestRedisStoreSharedAcrossLimiters:
    @classmethod
    async def test_redis__shared_store__multiple_limiters_share_counter(
        cls, redis_store: RedisStore
    ) -> None:
        """Two Limiters with different quotas but the same Redis store
        and overlapping keys hit the same counter. This is the basis
        for sub-app-local policies sharing one Redis backend in
        production deployments.
        """
        # Use fixed_window so remaining-count assertions reflect a simple
        # shared counter rather than token-bucket refill semantics.
        limiter_lenient = Limiter("100/m", store=redis_store, using="fixed_window")
        limiter_strict = Limiter("2/m", store=redis_store, using="fixed_window")

        # Two apps with the same path so the route_template part matches;
        # they only differ by which Limiter wraps them. Using two apps
        # avoids stacked-decorator collisions.
        app_lenient = FastAPI()
        setup_app(app_lenient)

        @app_lenient.get("/shared")
        @limiter_lenient.limit()
        async def lenient(request: Request) -> dict[str, bool]:
            return {"ok": True}

        app_strict = FastAPI()
        setup_app(app_strict)

        @app_strict.get("/shared")
        @limiter_strict.limit()
        async def strict(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async with asgi_client(app_lenient) as client_lenient:
            r1 = await client_lenient.get("/shared")
        assert r1.status_code == HTTPStatus.OK
        assert r1.headers["RateLimit-Remaining"] == "99"

        # The strict limiter sees the counter the lenient one already
        # incremented (same key in same Redis store).
        async with asgi_client(app_strict) as client_strict:
            r2 = await client_strict.get("/shared")
        assert r2.status_code == HTTPStatus.OK
        # Strict limiter quota is 2; one slot already consumed by the
        # lenient call above, so remaining should be 0 after this call.
        assert r2.headers["RateLimit-Remaining"] == "0"
