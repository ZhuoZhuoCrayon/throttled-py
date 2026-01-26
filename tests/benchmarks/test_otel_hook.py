from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest
from throttled import Hook, Throttled, per_sec
from throttled.utils import Benchmark

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from throttled import RateLimitResult

# Optional imports for OTel tests
try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from throttled.contrib.otel import OTelHook

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


class NoOpHook(Hook):
    """A hook that does nothing, used to measure hook system overhead."""

    def on_limit(self, *args, **kwargs) -> "RateLimitResult":  # noqa: PLR6301
        """Execute the next handler without any additional processing."""
        call_next: Callable[[], RateLimitResult] = args[0]
        return call_next()


def call_api(throttle: Throttled) -> bool:
    """Call the throttle limit API."""
    result: RateLimitResult = throttle.limit("/ping", cost=1)
    return result.limited


@pytest.mark.skip(reason="skip benchmarks")
class TestBenchmarkOTelHook:
    @classmethod
    def test_baseline_no_hook__serial(cls, benchmark: Benchmark) -> None:
        """Baseline: No hooks attached."""
        throttle: Throttled = Throttled(quota=per_sec(1_000_000))
        benchmark.serial(call_api, batch=100_000, throttle=throttle)

    @classmethod
    def test_noop_hook__serial(cls, benchmark: Benchmark) -> None:
        """Measure hook system overhead with a no-op hook."""
        throttle: Throttled = Throttled(quota=per_sec(1_000_000), hooks=[NoOpHook()])
        benchmark.serial(call_api, batch=100_000, throttle=throttle)

    @classmethod
    @pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")
    def test_otel_hook__serial(cls, benchmark: Benchmark) -> None:
        """Measure OTelHook overhead with real SDK."""
        # Setup minimal OTel provider
        reader: InMemoryMetricReader = InMemoryMetricReader()
        provider: MeterProvider = MeterProvider(metric_readers=[reader])
        otel_metrics.set_meter_provider(provider)

        # Create meter and hook (new API: meter DI)
        meter = otel_metrics.get_meter("benchmark")
        hook: OTelHook = OTelHook(meter)

        throttle: Throttled = Throttled(quota=per_sec(1_000_000), hooks=[hook])
        benchmark.serial(call_api, batch=100_000, throttle=throttle)
