"""Flask-specific rate-limit exception rendered as HTTP 429."""

from typing import TYPE_CHECKING, Any

from throttled.exceptions import LimitedError
from werkzeug.exceptions import TooManyRequests

from .headers import _inject_rate_limit_headers

if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIEnvironment

    from .headers import RateLimitContext


class RateLimitExceededError(TooManyRequests, LimitedError):
    """Raised by :class:`Limiter` when a view exceeds its quota.

    Subclasses :class:`werkzeug.exceptions.TooManyRequests`, so Flask
    renders it as HTTP 429 without any errorhandler registration, and
    :class:`throttled.exceptions.LimitedError`, so error handling
    shared with the core library (``except LimitedError`` or
    ``@app.errorhandler(LimitedError)``) keeps working.

    The default 429 response carries ``RateLimit-*`` and
    ``Retry-After`` headers through :meth:`get_headers`. Register
    ``@app.errorhandler(RateLimitExceededError)`` to customize the
    body; :attr:`rate_limit_context` exposes the result and policy.

    :param context: The :class:`RateLimitContext` carrying the
        rate-limit result and the header policy used to render the
        429 response.
    """

    description = "Rate limit exceeded"

    def __init__(self, context: "RateLimitContext") -> None:
        TooManyRequests.__init__(self)
        LimitedError.__init__(self, rate_limit_result=context.result)
        #: The decorator-owned rate-limit context.
        self.rate_limit_context: RateLimitContext = context

    def get_headers(
        self,
        environ: "WSGIEnvironment | None" = None,
        scope: dict[str, Any] | None = None,
    ) -> list[tuple[str, str]]:
        """Extend werkzeug's headers with ``RateLimit-*`` and ``Retry-After``.

        See draft-ietf-httpapi-ratelimit-headers and RFC 9110
        section 10.2.3.
        """
        headers: dict[str, str] = dict(super().get_headers(environ, scope))
        _inject_rate_limit_headers(
            headers,
            self.rate_limit_context,
            include_retry_after=True,
        )
        return list(headers.items())
