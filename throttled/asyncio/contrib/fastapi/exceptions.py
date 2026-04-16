"""FastAPI-specific rate-limit exception and HTTP 429 handler."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from throttled.exceptions import LimitedError

if TYPE_CHECKING:
    from fastapi import Request
    from throttled.asyncio.rate_limiter import RateLimitResult


class RateLimitExceededError(LimitedError):
    """Raised by :class:`Limiter` when a route exceeds its quota.

    :param result: The :class:`RateLimitResult` carrying
        limit/remaining/reset/retry fields.
    """

    def __init__(self, result: RateLimitResult) -> None:
        super().__init__(rate_limit_result=result)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Render :class:`RateLimitExceededError` as HTTP 429.

    Register on each :class:`FastAPI` app that uses rate-limited routes::

        app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)

    See draft-ietf-httpapi-ratelimit-headers and RFC 9110 section 10.2.3.

    :param request: Inbound request (required by Starlette signature).
    :param exc: The exception instance dispatched by Starlette.
    :returns: A 429 :class:`JSONResponse` with ``RateLimit-*`` and
        ``Retry-After`` headers.
    """
    headers: dict[str, str] = {}
    retry_after_sec: int = 0

    result: RateLimitResult | None = None
    if isinstance(exc, LimitedError):
        result = exc.rate_limit_result

    if result is not None and result.state is not None:
        state = result.state
        retry_after_sec = math.ceil(state.retry_after)
        headers["RateLimit-Limit"] = str(state.limit)
        headers["RateLimit-Remaining"] = str(state.remaining)
        headers["RateLimit-Reset"] = str(math.ceil(state.reset_after))
        headers["Retry-After"] = str(retry_after_sec)

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "retry_after": retry_after_sec,
        },
        headers=headers,
    )
