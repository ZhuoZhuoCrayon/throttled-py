"""Internal rate-limit header policy and shared renderer.

This module is internal to the FastAPI contrib. The decorator builds a
:class:`RateLimitContext`, the success-path middleware and the 429
exception handler render headers through the same
:func:`_inject_rate_limit_headers` helper. Header names live on
:class:`RateLimitHeaderPolicy`, so middleware and handler do not know
the literal strings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from throttled.asyncio.rate_limiter import RateLimitResult


#: ``request.state`` attribute name used by the decorator and the
#: middleware to share the per-request context.
_STATE_KEY: str = "_throttled_rate_limit_context"


@dataclass(frozen=True)
class RateLimitHeaderPolicy:
    """Header names used when rendering rate-limit metadata.

    Defaults follow draft-ietf-httpapi-ratelimit-headers and RFC 9110
    section 10.2.3 for ``Retry-After``.
    """

    #: Header name for the request quota in the current window.
    limit: str = "RateLimit-Limit"

    #: Header name for the remaining requests in the current window.
    remaining: str = "RateLimit-Remaining"

    #: Header name for the seconds until the quota resets.
    reset: str = "RateLimit-Reset"

    #: Header name for the seconds the client should wait before retrying.
    retry_after: str = "Retry-After"


@dataclass(frozen=True)
class RateLimitContext:
    """Per-request rate-limit decision and the policy used to render it.

    Built by :class:`Limiter` after a rate-limit check, attached to
    ``request.state`` for the success path, and carried by
    :class:`RateLimitExceededError` for the 429 path.
    """

    #: The rate-limit result produced by the underlying limiter.
    result: RateLimitResult

    #: The header policy that should be applied when rendering this context.
    headers: RateLimitHeaderPolicy


#: Singleton default header policy. The decorator references this
#: instance directly so the policy is visible as a constant rather
#: than allocated per request.
_DEFAULT_HEADER_POLICY: RateLimitHeaderPolicy = RateLimitHeaderPolicy()


def _inject_rate_limit_headers(
    headers: dict[str, str],
    context: RateLimitContext,
    *,
    include_retry_after: bool,
) -> None:
    """Apply ``context``'s rate-limit headers to ``headers``.

    Writes the ``RateLimit-Limit``, ``RateLimit-Remaining``, and
    ``RateLimit-Reset`` headers (or whatever names the policy carries)
    when the result has a state. ``Retry-After`` is only written when
    ``include_retry_after`` is true, which is the 429 path.

    :param headers: Mutable headers mapping to mutate in place.
    :param context: The decorator-owned context carrying both the
        result and the header-name policy.
    :param include_retry_after: ``True`` when called from the 429
        handler so the ``Retry-After`` header is set; ``False`` for the
        success-path middleware.
    """
    if context.result.state is None:
        return

    state = context.result.state
    policy = context.headers

    headers[policy.limit] = str(state.limit)
    headers[policy.remaining] = str(state.remaining)
    headers[policy.reset] = str(math.ceil(state.reset_after))

    if include_retry_after:
        headers[policy.retry_after] = str(math.ceil(state.retry_after))
