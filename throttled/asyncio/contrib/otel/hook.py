"""Async OpenTelemetry metrics hook for throttled-py."""

import time
from collections.abc import Awaitable, Callable

from throttled.asyncio.hooks import Hook, HookContext
from throttled.contrib.otel.hook import OTelHookBase
from throttled.rate_limiter import RateLimitResult


class OTelHook(OTelHookBase, Hook):
    """Async OpenTelemetry metrics hook using middleware pattern.

    Usage::

    >>> from opentelemetry.metrics import get_meter
    >>> from throttled.asyncio import Throttled
    >>> from throttled.asyncio.contrib.otel import OTelHook
    >>>
    >>> meter = get_meter("my-app")
    >>> hook = OTelHook(meter)
    >>> throttle = Throttled(key="/api", hooks=[hook])
    """

    async def on_limit(
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context: HookContext,
    ) -> RateLimitResult:
        """Wrap async rate limit check with timing and metrics recording."""
        start = time.perf_counter()
        result = await call_next()
        duration = time.perf_counter() - start

        self._record_metrics(context, result, duration=duration)
        return result
