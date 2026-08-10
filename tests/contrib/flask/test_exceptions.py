"""Tests for the dual-hierarchy ``RateLimitExceededError``.

The exception must satisfy two contracts at once: werkzeug renders it
as HTTP 429 with rate-limit headers (no handler registration needed),
and ``except LimitedError`` / ``@app.errorhandler(LimitedError)`` keep
working for code shared with the core library.
"""

from http import HTTPStatus

from flask import Flask, jsonify
from throttled.contrib.flask import (
    Limiter,
    RateLimitContext,
    RateLimitExceededError,
    RateLimitHeaderPolicy,
)
from throttled.exceptions import LimitedError
from throttled.rate_limiter import RateLimitResult
from throttled.store import MemoryStore
from werkzeug.exceptions import TooManyRequests


def _limited_context() -> RateLimitContext:
    result = RateLimitResult(limited=True, state_values=(1, 0, 60.0, 60.0))
    return RateLimitContext(result=result, headers=RateLimitHeaderPolicy())


class TestExceptionHierarchy:
    @classmethod
    def test_init__is_both_http_429_and_limited_error(cls) -> None:
        exc = RateLimitExceededError(_limited_context())

        assert isinstance(exc, TooManyRequests)
        assert isinstance(exc, LimitedError)
        assert exc.code == HTTPStatus.TOO_MANY_REQUESTS
        assert exc.description == "Rate limit exceeded"

    @classmethod
    def test_init__preserves_limited_error_contract(cls) -> None:
        """``rate_limit_result`` must carry the state that produced
        the 429 so shared error-handling code can read it."""
        context = _limited_context()
        exc = RateLimitExceededError(context)

        assert exc.rate_limit_result is context.result
        assert exc.rate_limit_context is context
        assert exc.rate_limit_result.state.remaining == 0

    @classmethod
    def test_get_headers__includes_rate_limit_and_retry_after(cls) -> None:
        """The 429 path renders headers from the exception itself, so
        they survive even without any registered errorhandler."""
        exc = RateLimitExceededError(_limited_context())

        headers = dict(exc.get_headers())
        assert headers["RateLimit-Limit"] == "1"
        assert headers["RateLimit-Remaining"] == "0"
        assert headers["RateLimit-Reset"] == "60"
        assert headers["Retry-After"] == "60"
        # Werkzeug's own headers (Content-Type) must be preserved.
        assert "Content-Type" in headers


class TestErrorHandlerDispatch:
    @classmethod
    def _build_limited_app(cls) -> tuple[Flask, Limiter]:
        limiter = Limiter("1/m", store=MemoryStore())
        app = Flask(__name__)
        limiter.init_app(app)

        @app.get("/items")
        @limiter.limit()
        def list_items() -> dict[str, bool]:
            return {"ok": True}

        return app, limiter

    @classmethod
    def test_errorhandler__limited_error__catches_contrib_exception(cls) -> None:
        """A handler registered for the core ``LimitedError`` must
        receive the contrib exception via MRO dispatch."""
        app, _ = cls._build_limited_app()
        caught: list[Exception] = []

        @app.errorhandler(LimitedError)
        def on_limited(exc: LimitedError):
            caught.append(exc)
            return jsonify(custom=True), HTTPStatus.TOO_MANY_REQUESTS

        client = app.test_client()
        assert client.get("/items").status_code == HTTPStatus.OK
        response = client.get("/items")

        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert response.get_json() == {"custom": True}
        assert isinstance(caught[0], RateLimitExceededError)

    @classmethod
    def test_errorhandler__exact_type__customizes_429_body(cls) -> None:
        """The documented customization point: register a handler for
        ``RateLimitExceededError`` and render your own body."""
        app, _ = cls._build_limited_app()

        @app.errorhandler(RateLimitExceededError)
        def on_exceeded(exc: RateLimitExceededError):
            # rate_limit_context is contrib-owned and never None, unlike
            # the Optional rate_limit_result inherited from LimitedError.
            state = exc.rate_limit_context.result.state
            body = jsonify(retry_after=state.retry_after)
            # get_headers() carries werkzeug's HTML Content-Type; drop it
            # when rendering a JSON body.
            headers = {
                name: value
                for name, value in exc.get_headers()
                if name.lower() != "content-type"
            }
            return body, HTTPStatus.TOO_MANY_REQUESTS, headers

        client = app.test_client()
        client.get("/items")
        response = client.get("/items")

        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
        assert response.get_json() == {"retry_after": 60.0}
        assert response.headers["RateLimit-Remaining"] == "0"
