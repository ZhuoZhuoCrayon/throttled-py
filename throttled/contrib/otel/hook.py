"""OpenTelemetry metrics hook for throttled-py."""

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from opentelemetry.metrics import Meter
from throttled.hooks import Hook, HookContext
from throttled.rate_limiter import RateLimitResult

if TYPE_CHECKING:
    from opentelemetry.metrics import Counter, Histogram


class OTelHook(Hook):
    """OpenTelemetry metrics hook using middleware pattern.

    Collects the following metrics:

    - throttled.requests (Counter): Number of rate limit checks with result dimension
    - throttled.duration (Histogram): Duration of rate limit checks in seconds

    Attributes (without throttled. prefix for conciseness):
    - key: The rate limit key
    - algorithm: The rate limiting algorithm
    - store_type: The storage backend type
    - result: "allowed" or "denied"

    Usage::

    >>> from opentelemetry.metrics import get_meter
    >>> from throttled import Throttled
    >>> from throttled.contrib.otel import OTelHook
    >>>
    >>> meter = get_meter("my-app")
    >>> hook = OTelHook(meter)
    >>> throttle = Throttled(key="/api", hooks=[hook])
    """

    METRIC_REQUESTS = "throttled.requests"
    METRIC_DURATION = "throttled.duration"

    def __init__(self, meter: Meter):
        """Initialize OTelHook.

        :param meter: OpenTelemetry Meter instance.
        """
        self._meter = meter

        self._requests: Counter = self._meter.create_counter(
            name=self.METRIC_REQUESTS,
            description="Number of rate limit checks",
            unit="1",
        )
        self._latency: Histogram = self._meter.create_histogram(
            name=self.METRIC_DURATION,
            description="Duration of rate limit checks",
            unit="s",
        )

    def on_limit(
        self,
        call_next: Callable[[], RateLimitResult],
        context: HookContext,
    ) -> RateLimitResult:
        """Wrap rate limit check with timing and metrics recording."""
        start = time.perf_counter()

        result = call_next()

        latency = time.perf_counter() - start

        attributes = {
            "key": context.key,
            "algorithm": context.algorithm,
            "store_type": context.store_type,
            "result": "denied" if result.limited else "allowed",
        }

        self._requests.add(context.cost, attributes)
        self._latency.record(latency, attributes)

        return result
