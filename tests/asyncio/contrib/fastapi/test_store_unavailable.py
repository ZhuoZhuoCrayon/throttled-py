"""Tests for FastAPI contrib ``StoreUnavailableError`` HTTP 503 mapping.

Covers the v3 design contract:

- Default path raises ``HTTPException(503)`` with a JSON detail body and
  emits one log record.
- A user-registered ``StoreUnavailableError`` handler preempts the default,
  and the library emits no store-unavailable log.
- No ``RateLimit-*`` or ``Retry-After`` headers are returned on the 503
  path because no reliable rate-limit state exists.
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from throttled.asyncio.contrib.fastapi import Limiter
from throttled.asyncio.contrib.fastapi import limiter as limiter_module
from throttled.exceptions import BaseThrottledError, StoreUnavailableError

from ...store.unavailable import OperationUnavailableStore
from .conftest import asgi_client, setup_app

if TYPE_CHECKING:
    from starlette.requests import Request as StarletteRequest


_LIMITER_LOGGER_NAME = "throttled.asyncio.contrib.fastapi.limiter"


@pytest.mark.asyncio
class TestStoreUnavailableDefault:
    @classmethod
    async def test_default__returns_503_json(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No handler registered: 503 JSON body + one ERROR log record."""
        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
            async with asgi_client(app) as client:
                response = await client.get("/x")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Rate limit store unavailable"}

        store_records = [r for r in caplog.records if r.name == _LIMITER_LOGGER_NAME]
        assert len(store_records) == 1
        assert store_records[0].getMessage() == limiter_module._STORE_UNAVAILABLE_LOG_MSG
        assert store_records[0].levelno == logging.ERROR
        assert store_records[0].exc_info is not None
        assert store_records[0].exc_info[0] is StoreUnavailableError

    @classmethod
    async def test_default__omits_rate_limit_and_retry_after_headers(cls) -> None:
        """No ``RateLimit-*`` or ``Retry-After`` headers on the 503 path."""
        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = FastAPI()
        setup_app(app)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        async with asgi_client(app) as client:
            response = await client.get("/x")

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert "ratelimit-limit" not in response.headers
        assert "ratelimit-remaining" not in response.headers
        assert "ratelimit-reset" not in response.headers
        assert "retry-after" not in response.headers


@pytest.mark.asyncio
class TestStoreUnavailableOverride:
    @classmethod
    async def test_override__user_handler_runs_and_library_emits_no_log(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Registering an exact handler preempts the default and
        suppresses the library's store-unavailable log record."""

        async def custom_handler(
            request: StarletteRequest, exc: Exception
        ) -> JSONResponse:
            return JSONResponse(
                status_code=HTTPStatus.BAD_GATEWAY,
                content={"detail": "store down"},
            )

        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = FastAPI()
        setup_app(app)
        app.add_exception_handler(StoreUnavailableError, custom_handler)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
            async with asgi_client(app) as client:
                response = await client.get("/x")

        assert response.status_code == HTTPStatus.BAD_GATEWAY
        assert response.json() == {"detail": "store down"}

        store_records = [r for r in caplog.records if r.name == _LIMITER_LOGGER_NAME]
        assert store_records == []


@pytest.mark.asyncio
class TestStoreUnavailableLimitations:
    @classmethod
    async def test_broader_handler__does_not_preempt_default_503(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A broader catch (e.g. ``BaseThrottledError``) does not preempt
        the default 503. The wrapper catches ``StoreUnavailableError``
        before Starlette's MRO-based dispatch can run, so only an exact
        ``StoreUnavailableError`` registration is consulted.
        """
        broader_called: dict[str, bool] = {"hit": False}

        async def broader_handler(
            request: StarletteRequest, exc: Exception
        ) -> JSONResponse:
            broader_called["hit"] = True
            return JSONResponse(
                status_code=HTTPStatus.BAD_GATEWAY,
                content={"detail": "broader handler ran"},
            )

        limiter = Limiter("5/s", store=OperationUnavailableStore())
        app = FastAPI()
        setup_app(app)
        app.add_exception_handler(BaseThrottledError, broader_handler)

        @app.get("/x")
        @limiter.limit()
        async def x(request: Request) -> dict[str, bool]:
            return {"ok": True}

        with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
            async with asgi_client(app) as client:
                response = await client.get("/x")

        # Default 503 path still wins, broader handler never runs.
        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json() == {"detail": "Rate limit store unavailable"}
        assert broader_called["hit"] is False

        # The library still emits its store-unavailable log on this path
        # because the broader handler did not preempt the default.
        store_records = [r for r in caplog.records if r.name == _LIMITER_LOGGER_NAME]
        assert len(store_records) == 1
        assert store_records[0].getMessage() == limiter_module._STORE_UNAVAILABLE_LOG_MSG
        assert store_records[0].levelno == logging.ERROR
        assert store_records[0].exc_info is not None
        assert store_records[0].exc_info[0] is StoreUnavailableError
