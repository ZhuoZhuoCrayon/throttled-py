"""Tests for RateLimitExceededError and rate_limit_exceeded_handler."""

from __future__ import annotations

import math
from http import HTTPStatus

import httpx
import pytest
from fastapi import FastAPI
from throttled.asyncio.contrib.fastapi import (
    RateLimitExceededError,
    rate_limit_exceeded_handler,
)
from throttled.asyncio.rate_limiter import RateLimitResult
from throttled.exceptions import LimitedError


async def _limited_response(
    result: RateLimitResult,
) -> httpx.Response:
    app = FastAPI()
    app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)

    @app.get("/limited")
    async def limited() -> dict[str, bool]:
        raise RateLimitExceededError(result)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get("/limited")


class TestRateLimitExceededError:
    @classmethod
    def test_rate_limit_exceeded_error__is_limited_error_subclass(
        cls,
    ) -> None:
        assert issubclass(RateLimitExceededError, LimitedError)


@pytest.mark.asyncio
class TestRateLimitExceededHandler:
    @classmethod
    async def test_rate_limit_exceeded_handler__returns_status_429(
        cls,
    ) -> None:
        result = RateLimitResult(
            limited=True,
            state_values=(100, 0, 60.0, 1.5),
        )
        response = await _limited_response(result)
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS

    @classmethod
    async def test_rate_limit_exceeded_handler__headers__follow_ietf_spec(
        cls,
    ) -> None:
        result = RateLimitResult(
            limited=True,
            state_values=(100, 0, 60.0, 1.5),
        )
        response = await _limited_response(result)
        assert response.headers["RateLimit-Limit"] == "100"
        assert response.headers["RateLimit-Remaining"] == "0"
        assert response.headers["RateLimit-Reset"] == str(math.ceil(60.0))
        assert response.headers["Retry-After"] == str(math.ceil(1.5))

    @classmethod
    async def test_rate_limit_exceeded_handler__retry_after__body_matches_header(
        cls,
    ) -> None:
        result = RateLimitResult(
            limited=True,
            state_values=(10, 0, 5.0, 2.3),
        )
        response = await _limited_response(result)
        body = response.json()
        assert body["retry_after"] == int(response.headers["Retry-After"])
        assert body["retry_after"] == math.ceil(2.3)
