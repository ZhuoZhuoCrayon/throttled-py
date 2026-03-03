from collections.abc import Awaitable, Callable
from unittest.mock import MagicMock

import pytest
from throttled.asyncio import Throttled, per_sec, store
from throttled.asyncio.contrib.otel import OTelHook
from throttled.asyncio.hooks import Hook, build_hook_chain
from throttled.constants import RateLimiterType
from throttled.hooks import HookContext
from throttled.rate_limiter import RateLimitResult

# Test constants
EXPECTED_CALL_COUNT = 2
EXPECTED_CUSTOM_COST = 5
MIN_RETRY_DURATION = 0.9


@pytest.fixture
def mock_meter() -> MagicMock:
    """Create a mock meter for OTelHook.

    OTelHook calls meter.create_counter() and meter.create_histogram()
    in __init__, so we mock their return values.
    """
    meter: MagicMock = MagicMock(name="Meter")
    meter.create_counter.return_value = MagicMock(name="Counter")
    meter.create_histogram.return_value = MagicMock(name="Histogram")
    return meter


@pytest.mark.asyncio
class TestOTelHook:
    @classmethod
    async def test_creates_counter_and_histogram(cls, mock_meter: MagicMock) -> None:
        """Verify OTelHook creates the expected instruments."""
        _ = OTelHook(mock_meter)

        mock_meter.create_counter.assert_called_once_with(
            name=OTelHook.METRIC_REQUESTS,
            description="Number of rate limit checks",
            unit="1",
        )
        mock_meter.create_histogram.assert_called_once_with(
            name=OTelHook.METRIC_DURATION,
            description="Duration of rate limit checks",
            unit="s",
        )

    @classmethod
    async def test_allowed_request__records_metrics(cls, mock_meter: MagicMock) -> None:
        """Verify metrics are recorded with correct attributes when allowed."""
        hook: OTelHook = OTelHook(mock_meter)
        counter: MagicMock = mock_meter.create_counter.return_value
        histogram: MagicMock = mock_meter.create_histogram.return_value

        throttle: Throttled = Throttled(key="test-key", quota=per_sec(10), hooks=[hook])
        result: RateLimitResult = await throttle.limit()

        assert result.limited is False

        expected_attrs: dict[str, str] = {
            "key": "test-key",
            "algorithm": "token_bucket",
            "store_type": "memory",
            "result": "allowed",
        }

        counter.add.assert_called_once()
        cost, attrs = counter.add.call_args.args
        assert cost == 1
        assert attrs == expected_attrs

        histogram.record.assert_called_once()
        duration, hist_attrs = histogram.record.call_args.args
        assert duration >= 0
        assert hist_attrs == expected_attrs

    @classmethod
    async def test_denied_request__records_metrics(cls, mock_meter: MagicMock) -> None:
        """Verify metrics are recorded with result=denied when denied."""
        hook: OTelHook = OTelHook(mock_meter)
        counter: MagicMock = mock_meter.create_counter.return_value

        throttle: Throttled = Throttled(key="test-key", quota=per_sec(1), hooks=[hook])

        # First request - allowed
        await throttle.limit()
        # Second request - denied
        result: RateLimitResult = await throttle.limit()

        assert result.limited is True

        # Check second call has result=denied
        calls = counter.add.call_args_list
        assert len(calls) == EXPECTED_CALL_COUNT
        _, denied_attrs = calls[1].args
        assert denied_attrs["result"] == "denied"

    @classmethod
    async def test_custom_cost__recorded(cls, mock_meter: MagicMock) -> None:
        """Verify custom cost is recorded correctly."""
        hook: OTelHook = OTelHook(mock_meter)
        counter: MagicMock = mock_meter.create_counter.return_value

        throttle: Throttled = Throttled(key="test-key", quota=per_sec(100), hooks=[hook])
        await throttle.limit(cost=EXPECTED_CUSTOM_COST)

        cost, _ = counter.add.call_args.args
        assert cost == EXPECTED_CUSTOM_COST

    @classmethod
    @pytest.mark.parametrize("algorithm", RateLimiterType.choice())
    async def test_algorithm_attribute(
        cls, mock_meter: MagicMock, algorithm: str
    ) -> None:
        """Verify algorithm attribute is set correctly for all algorithms."""
        hook: OTelHook = OTelHook(mock_meter)
        counter: MagicMock = mock_meter.create_counter.return_value

        throttle: Throttled = Throttled(
            key="test-key",
            quota=per_sec(10),
            using=algorithm,
            hooks=[hook],
        )
        await throttle.limit()

        _, attrs = counter.add.call_args.args
        assert attrs["algorithm"] == algorithm

    @classmethod
    async def test_duration__includes_retry_wait_time(
        cls, mock_meter: MagicMock
    ) -> None:
        """Verify duration includes the entire limit() time including retry waits.

        When a request is initially denied but succeeds after retry,
        the recorded duration should include the wait time.
        """
        hook: OTelHook = OTelHook(mock_meter)
        histogram: MagicMock = mock_meter.create_histogram.return_value

        throttle: Throttled = Throttled(
            key="test-key",
            quota=per_sec(1),
            timeout=2,  # Enable retry
            hooks=[hook],
        )

        # First call: allowed immediately
        await throttle.limit()
        # Second call: denied initially, waits ~1s, then succeeds
        await throttle.limit()

        # Check the second call's duration (should be >= 1s due to retry wait)
        calls = histogram.record.call_args_list
        assert len(calls) == EXPECTED_CALL_COUNT

        second_duration, _ = calls[1].args
        # Duration should be at least 0.9s (allowing some tolerance)
        assert second_duration >= MIN_RETRY_DURATION, (
            f"Duration {second_duration}s should include retry wait time "
            f"(>= {MIN_RETRY_DURATION}s)"
        )


@pytest.mark.asyncio
class TestBuildHookChain:
    @classmethod
    async def test_empty_hooks__returns_do_limit_directly(cls) -> None:
        """Verify build_hook_chain returns do_limit unchanged when hooks is empty."""
        sentinel = RateLimitResult(limited=False, state_values=(100, 99, 60.0, 0.0))

        async def do_limit():
            return sentinel

        context = HookContext(
            key="k", cost=1, algorithm="token_bucket", store_type="memory"
        )

        chain = build_hook_chain([], do_limit, context)

        assert chain is do_limit

    @classmethod
    async def test_hook_exception__skipped_and_chain_continues(
        cls, mock_meter: MagicMock
    ) -> None:
        """Verify a hook that raises is skipped and rate limiting still works."""

        class _FailingHook(Hook):
            async def on_limit(  # noqa: PLR6301
                self,
                call_next: Callable[[], Awaitable[RateLimitResult]],
                context: HookContext,
            ) -> RateLimitResult:
                raise RuntimeError("boom")

        hook: OTelHook = OTelHook(mock_meter)
        throttle: Throttled = Throttled(
            key="test-key",
            quota=per_sec(10),
            store=store.MemoryStore(),
            hooks=[_FailingHook(), hook],
        )

        result: RateLimitResult = await throttle.limit()

        assert result.limited is False
        # OTelHook (second in chain) should still record metrics
        mock_meter.create_counter.return_value.add.assert_called_once()
