"""End-to-end tests driving a real FastAPI app through HTTPX."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import (
    FastAPI,
    Request,  # noqa: TCH002 (runtime use: FastAPI signature inspection)
)
from starlette.staticfiles import StaticFiles
from throttled.asyncio.contrib.fastapi import (
    Limiter,
    RateLimitExceededError,
    RateLimitMiddleware,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.store import MemoryStore

from .conftest import ALGORITHMS, asgi_client

if TYPE_CHECKING:
    from collections.abc import Callable


def _register_items_endpoint(app: FastAPI, limiter: Limiter) -> None:
    @app.get("/items")
    @limiter.limit()
    async def list_items(request: Request) -> dict[str, str]:
        return {"ok": "yes"}


def _setup_app(app: FastAPI) -> None:
    """Register middleware and exception handler on a FastAPI app."""
    app.add_middleware(RateLimitMiddleware)
    app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)


class TestLimiterInit:
    @classmethod
    def test_init__quota_is_none__raises_type_error(cls) -> None:
        """A missing quota must fail loudly."""
        with pytest.raises(TypeError, match=r"requires an explicit quota"):
            Limiter(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
class TestLimiterLimit:
    @classmethod
    async def test_limit__below_quota__allows_requests(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Requests under the quota pass through unchanged."""
        app, limiter = build_app(quota="2/s")
        _register_items_endpoint(app, limiter)

        async for client in asgi_client(app):
            assert (await client.get("/items")).status_code == HTTPStatus.OK
            assert (await client.get("/items")).status_code == HTTPStatus.OK

    @classmethod
    async def test_limit__quota_exhausted__returns_429(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Second request exceeds a ``1/s`` quota and must 429."""
        app, limiter = build_app(quota="1/s")
        _register_items_endpoint(app, limiter)

        async for client in asgi_client(app):
            assert (await client.get("/items")).status_code == HTTPStatus.OK
            assert (
                await client.get("/items")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_limit__429_response__carries_ietf_headers_and_body(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """429 carries draft-ietf-httpapi-ratelimit headers and body."""
        app, limiter = build_app(quota="1/s")
        _register_items_endpoint(app, limiter)

        async for client in asgi_client(app):
            await client.get("/items")
            response = await client.get("/items")
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert response.headers["RateLimit-Limit"] == "1"
        assert response.headers["RateLimit-Remaining"] == "0"
        assert "RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers
        body = response.json()
        assert body["detail"] == "Rate limit exceeded"
        assert body["retry_after"] == int(response.headers["Retry-After"])

    @classmethod
    async def test_limit__sync_function__raises_typeerror_at_decoration(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Sync endpoints are rejected eagerly at decoration time."""
        _, limiter = build_app()
        with pytest.raises(TypeError, match=r"cannot wrap sync route function"):

            @limiter.limit()  # type: ignore[arg-type]
            def sync_handler(request: Request) -> str:
                return "no"

    @classmethod
    async def test_limit__path_parameters__share_route_template_key(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """``/users/{user_id}`` must share one rate-limit key across
        concrete IDs."""
        app, limiter = build_app(quota="1/s")

        @app.get("/users/{user_id}")
        @limiter.limit()
        async def get_user(request: Request, user_id: int) -> dict[str, int]:
            return {"id": user_id}

        async for client in asgi_client(app):
            assert (await client.get("/users/1")).status_code == HTTPStatus.OK
            assert (
                await client.get("/users/2")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_limit__arbitrary_request_param_name__accepted(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """FastAPI users may name the ``Request`` parameter anything."""
        app, limiter = build_app(quota="10/s")

        @app.get("/x")
        @limiter.limit()
        async def handler(req: Request) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            assert (await client.get("/x")).status_code == HTTPStatus.OK

    @classmethod
    async def test_limit__per_route_quota__overrides_default(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Per-route quota tighter than the instance default wins."""
        app, limiter = build_app(quota="1000/s")

        @app.get("/tight")
        @limiter.limit("1/s")
        async def tight(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            assert (await client.get("/tight")).status_code == HTTPStatus.OK
            assert (
                await client.get("/tight")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_limit__per_route_key_func__overrides_default(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Per-route key_func swaps the principal extractor for that
        route only."""
        app, limiter = build_app(quota="1/s", key_func=lambda req: "shared")

        @app.get("/per-user")
        @limiter.limit(key_func=lambda req: req.headers["x-user"])
        async def per_user(
            request: Request,
        ) -> dict[str, bool]:
            return {"ok": True}

        @app.get("/shared")
        @limiter.limit()
        async def shared(
            request: Request,
        ) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            assert (
                await client.get("/per-user", headers={"x-user": "alice"})
            ).status_code == HTTPStatus.OK
            assert (
                await client.get("/per-user", headers={"x-user": "bob"})
            ).status_code == HTTPStatus.OK
            assert (
                await client.get("/per-user", headers={"x-user": "alice"})
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS
            assert (await client.get("/shared")).status_code == HTTPStatus.OK
            assert (
                await client.get("/shared")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_limit__mounted_subapps__do_not_share_key(
        cls,
    ) -> None:
        """Mounted sub-apps with the same child path must keep
        independent rate-limit keys. Each sub-app registers its
        own middleware and exception handler (app-local model)."""
        store = MemoryStore()
        limiter = Limiter("1/s", store=store)

        api = FastAPI()
        admin = FastAPI()

        _setup_app(api)
        _setup_app(admin)

        @api.get("/users/{user_id}")
        @limiter.limit()
        async def api_user(request: Request, user_id: int) -> dict[str, int]:
            return {"id": user_id}

        @admin.get("/users/{user_id}")
        @limiter.limit()
        async def admin_user(request: Request, user_id: int) -> dict[str, int]:
            return {"id": user_id}

        root = FastAPI()
        root.mount("/api", api)
        root.mount("/admin", admin)

        async for client in asgi_client(root):
            assert (await client.get("/api/users/1")).status_code == HTTPStatus.OK
            assert (await client.get("/admin/users/1")).status_code == HTTPStatus.OK
            assert (
                await client.get("/api/users/2")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS
            assert (
                await client.get("/admin/users/2")
            ).status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_limit__non_fastapi_mounts__are_skipped(
        cls,
    ) -> None:
        """Non-FastAPI mounts (StaticFiles, etc.) do not interfere."""
        limiter = Limiter("1/s", store=MemoryStore())

        root = FastAPI()
        _setup_app(root)

        @root.get("/items")
        @limiter.limit()
        async def items(request: Request) -> dict[str, str]:
            return {"ok": "yes"}

        root.mount("/static", StaticFiles(directory="."))

        async for client in asgi_client(root):
            assert (await client.get("/items")).status_code == HTTPStatus.OK


@pytest.mark.asyncio
class TestSuccessHeaders:
    @classmethod
    async def test_limit__success__dict_return__headers_present(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Dict return (no Response object) still gets RateLimit-*
        headers via middleware. This is the v3 core improvement."""
        app, limiter = build_app(quota="10/s")

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            resp = await client.get("/x")
        assert resp.status_code == HTTPStatus.OK
        assert resp.headers["RateLimit-Limit"] == "10"
        assert resp.headers["RateLimit-Remaining"] == "9"
        assert "RateLimit-Reset" in resp.headers

    @classmethod
    async def test_limit__success__remaining_decrements(
        cls,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """RateLimit-Remaining decrements with each request."""
        app, limiter = build_app(quota="5/s")

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            r1 = await client.get("/x")
            r2 = await client.get("/x")
        assert r1.headers["RateLimit-Remaining"] == "4"
        assert r2.headers["RateLimit-Remaining"] == "3"


@pytest.mark.asyncio
class TestLimiterAlgorithm:
    @classmethod
    @pytest.mark.parametrize("algorithm", ALGORITHMS)
    async def test_limit__each_algorithm__returns_429_after_exhaustion(
        cls,
        algorithm: str,
        build_app: Callable[..., tuple[FastAPI, Limiter]],
    ) -> None:
        """Every supported algorithm must 429 when exhausted."""
        app, limiter = build_app(quota="1/s", using=algorithm)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async for client in asgi_client(app):
            assert (await client.get("/x")).status_code == HTTPStatus.OK
            await client.get("/x")
            assert (await client.get("/x")).status_code == HTTPStatus.TOO_MANY_REQUESTS
