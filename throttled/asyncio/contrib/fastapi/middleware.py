"""ASGI middleware for rate-limit header injection on successful responses."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response
    from throttled.asyncio.rate_limiter import RateLimitResult

_STATE_KEY: str = "_throttled_rate_limit_result"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Inject ``RateLimit-*`` headers on successful responses.

    Reads the :class:`RateLimitResult` stored on ``request.state``
    by the :meth:`Limiter.limit` decorator wrapper and injects
    ``RateLimit-Limit``, ``RateLimit-Remaining``, and
    ``RateLimit-Reset`` headers.

    The decorator raises :class:`RateLimitExceededError` on quota
    exhaustion, which is handled by a separately registered exception
    handler. This middleware only handles the success path.
    """

    async def dispatch(  # noqa: PLR6301
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and inject rate-limit headers.

        :param request: Incoming HTTP request.
        :param call_next: Calls the next middleware or the route.
        :returns: The response with ``RateLimit-*`` headers when
            a rate-limit result is available.
        """
        response: Response = await call_next(request)
        result: RateLimitResult | None = getattr(request.state, _STATE_KEY, None)
        if result is not None and result.state is not None:
            state = result.state
            response.headers["RateLimit-Limit"] = str(state.limit)
            response.headers["RateLimit-Remaining"] = str(state.remaining)
            response.headers["RateLimit-Reset"] = str(math.ceil(state.reset_after))
        return response
