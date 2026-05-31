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
    from collections.abc import Awaitable, Callable

    import httpx
    from starlette.requests import Request as StarletteRequest


_LIMITER_LOGGER_NAME = "throttled.asyncio.contrib.fastapi.limiter"


class _CustomStoreUnavailableError(StoreUnavailableError):
    """A downstream store's finer-grained outage exception."""


async def _custom_503_override(
    request: StarletteRequest, exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTPStatus.BAD_GATEWAY,
        content={"detail": "store down"},
    )


def build_unavailable_app(
    *,
    handler_type: type[Exception] | None = None,
    handler: Callable[..., Awaitable[JSONResponse]] | None = None,
) -> FastAPI:
    """Build a FastAPI app whose only route is rate-limited by a store
    that always raises ``StoreUnavailableError``.
    """
    limiter = Limiter("5/s", store=OperationUnavailableStore())
    app = FastAPI()
    setup_app(app)
    if handler_type is not None and handler is not None:
        app.add_exception_handler(handler_type, handler)

    @app.get("/")
    @limiter.limit()
    async def endpoint(request: Request) -> dict[str, bool]:
        return {"ok": True}

    return app


async def call_route(app: FastAPI, caplog: pytest.LogCaptureFixture) -> httpx.Response:
    """Call the app's rate-limited route with the limiter logger captured
    at ERROR level."""
    with caplog.at_level(logging.ERROR, logger=_LIMITER_LOGGER_NAME):
        async with asgi_client(app) as client:
            return await client.get("/")


def _store_unavailable_records(
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    # Scope to the limiter logger so unrelated records don't skew the count.
    return [r for r in caplog.records if r.name == _LIMITER_LOGGER_NAME]


def assert_store_unavailable_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = _store_unavailable_records(caplog)
    assert len(records) == 1
    record = records[0]
    assert record.getMessage() == limiter_module._STORE_UNAVAILABLE_LOG_MSG
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert record.exc_info[0] is StoreUnavailableError


def assert_no_store_unavailable_log(caplog: pytest.LogCaptureFixture) -> None:
    assert _store_unavailable_records(caplog) == []


@pytest.mark.asyncio
class TestStoreUnavailable:
    @classmethod
    async def test_default__returns_503_without_rate_limit_headers(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No handler registered: 503 JSON body, one ERROR log record,
        and no ``RateLimit-*`` / ``Retry-After`` headers."""
        app = build_unavailable_app()
        response = await call_route(app, caplog)

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": "Rate limit store unavailable"}
        assert "ratelimit-limit" not in response.headers
        assert "ratelimit-remaining" not in response.headers
        assert "ratelimit-reset" not in response.headers
        assert "retry-after" not in response.headers

        assert_store_unavailable_logged_once(caplog)

    @classmethod
    @pytest.mark.parametrize(
        "handler_type",
        [
            pytest.param(StoreUnavailableError, id="exact-handler"),
            pytest.param(BaseThrottledError, id="base-class-handler"),
        ],
    )
    async def test_handler__preempts_default_503(
        cls,
        handler_type: type[Exception],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A handler whose class is in the raised exception's MRO
        (exact ``StoreUnavailableError`` or a base such as
        ``BaseThrottledError``) preempts the default 503 and suppresses
        the library's store-unavailable log.
        """
        app = build_unavailable_app(
            handler_type=handler_type,
            handler=_custom_503_override,
        )
        response = await call_route(app, caplog)

        assert response.status_code == HTTPStatus.BAD_GATEWAY
        assert response.json() == {"detail": "store down"}
        assert_no_store_unavailable_log(caplog)

    @classmethod
    async def test_global_exception_handler__does_not_preempt_default_503(
        cls,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Starlette routes ``Exception``/500 handlers through
        ``ServerErrorMiddleware``, which re-raises after handling, so a
        global handler must NOT preempt the default 503. Doing so would
        surface raw ``StoreUnavailableError`` to the transport and
        suppress the library's outage log.
        """
        global_called: dict[str, bool] = {"hit": False}

        async def global_handler(
            request: StarletteRequest, exc: Exception
        ) -> JSONResponse:
            global_called["hit"] = True
            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content={"detail": "global handler ran"},
            )

        app = build_unavailable_app(handler_type=Exception, handler=global_handler)
        response = await call_route(app, caplog)

        assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert response.json() == {"detail": "Rate limit store unavailable"}
        assert global_called["hit"] is False
        assert_store_unavailable_logged_once(caplog)


@pytest.mark.parametrize(
    ("registered", "raised", "expected"),
    [
        pytest.param(
            StoreUnavailableError, StoreUnavailableError, True, id="exact-match"
        ),
        pytest.param(BaseThrottledError, StoreUnavailableError, True, id="base-via-mro"),
        pytest.param(
            _CustomStoreUnavailableError,
            _CustomStoreUnavailableError,
            True,
            id="subclass-via-mro",
        ),
        pytest.param(Exception, StoreUnavailableError, False, id="exception-excluded"),
        pytest.param(None, StoreUnavailableError, False, id="no-handler"),
    ],
)
def test_has_exception_handler__matches_via_mro_excluding_exception(
    registered: type[Exception] | None,
    raised: type[Exception],
    expected: bool,
) -> None:
    """``_has_exception_handler`` walks the raised type's MRO so exact,
    base-class, and subclass handlers all match, while a global
    ``Exception`` handler and the no-handler case do not.

    This is the unit-level counterpart to the request-path tests: a
    subclass outage cannot reach the wrapper through a real store
    (``store/wraps.py`` always raises the base ``StoreUnavailableError``),
    so the subclass contract is verified directly here.
    """
    app = FastAPI()
    if registered is not None:
        app.add_exception_handler(registered, _custom_503_override)

    assert limiter_module._has_exception_handler(app, raised) is expected
