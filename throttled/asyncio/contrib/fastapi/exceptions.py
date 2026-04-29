"""FastAPI-specific rate-limit exception and HTTP 429 handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse
from throttled.exceptions import LimitedError

from .headers import _inject_rate_limit_headers

if TYPE_CHECKING:
    from fastapi import Request

    from .headers import RateLimitContext


class RateLimitExceededError(LimitedError):
    """Raised by :class:`Limiter` when a route exceeds its quota.

    The :func:`rate_limit_exceeded_handler` reads
    :attr:`rate_limit_context` to render ``RateLimit-*`` and
    ``Retry-After`` headers on the 429 response.

    :param context: The :class:`RateLimitContext` carrying the
        rate-limit result and the header policy used to render the
        429 response.
    """

    def __init__(self, context: RateLimitContext) -> None:
        super().__init__(rate_limit_result=context.result)
        #: The decorator-owned rate-limit context.
        self.rate_limit_context: RateLimitContext = context


async def rate_limit_exceeded_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Render :class:`RateLimitExceededError` as HTTP 429.

    Register on each :class:`FastAPI` app that uses rate-limited routes::

        app.add_exception_handler(RateLimitExceededError, rate_limit_exceeded_handler)

    The wait time for the client is delivered through the standard
    HTTP ``Retry-After`` header. The body matches FastAPI's
    :class:`fastapi.HTTPException` shape with a ``detail`` field only.

    See draft-ietf-httpapi-ratelimit-headers and RFC 9110 section 10.2.3.

    :param request: Inbound request (required by Starlette signature).
    :param exc: The exception instance dispatched by Starlette.
    :returns: A 429 :class:`JSONResponse` with ``RateLimit-*`` and
        ``Retry-After`` headers.
    """
    headers: dict[str, str] = {}

    if isinstance(exc, RateLimitExceededError):
        _inject_rate_limit_headers(
            headers,
            exc.rate_limit_context,
            include_retry_after=True,
        )

    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
        headers=headers,
    )
