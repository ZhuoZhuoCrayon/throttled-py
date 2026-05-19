"""ASGI middleware for ``RateLimit-*`` headers on checked routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from .headers import _STATE_KEY, _inject_rate_limit_headers

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

    from .headers import RateLimitContext


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Add ``RateLimit-*`` headers to responses from rate-limit-checked routes.

    Reads the :class:`RateLimitContext` stored on ``request.state`` by
    the :meth:`Limiter.limit` decorator wrapper and applies the
    decorator's header policy to the response. Header names live on
    the policy carried by the context.

    The exception handler renders quota exhaustion as HTTP 429 and adds
    ``Retry-After``. This middleware only applies headers from the
    decorator-produced context after ``call_next()`` returns.
    """

    async def dispatch(  # noqa: PLR6301
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and inject rate-limit headers.

        :param request: Incoming HTTP request.
        :param call_next: Calls the next middleware or the route.
        :returns: The response, with ``RateLimit-*`` headers added
            when the route ran under a rate-limit check.
        """
        response: Response = await call_next(request)
        context: RateLimitContext | None = getattr(request.state, _STATE_KEY, None)
        if context is not None:
            rate_limit_headers: dict[str, str] = {}
            _inject_rate_limit_headers(
                rate_limit_headers,
                context,
                include_retry_after=False,
            )
            response.headers.update(rate_limit_headers)
        return response
