import logging
from collections.abc import Awaitable, Callable
from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest
from throttled import (
    HookContext,
    RateLimiterType,
    RateLimitResult,
    Throttled,
    per_sec,
)
from throttled.asyncio.hooks import Hook as AsyncHook
from throttled.constants import StoreType
from throttled.hooks import Hook, build_hook_chain


@pytest.fixture
def hook_context() -> HookContext:
    """Create a sample HookContext for testing."""
    return HookContext(
        key="test_key",
        cost=1,
        algorithm=RateLimiterType.TOKEN_BUCKET.value,
        store_type=StoreType.MEMORY.value,
    )


@pytest.fixture
def rate_limit_result() -> RateLimitResult:
    """Create a RateLimitResult for testing."""
    return RateLimitResult(limited=False, state_values=(100, 99, 60.0, 0.0))


class TestHookContext:
    @classmethod
    def test_attributes(cls, hook_context: HookContext) -> None:
        """HookContext should have correct attributes."""
        assert hook_context.key == "test_key"
        assert hook_context.cost == 1
        assert hook_context.algorithm == RateLimiterType.TOKEN_BUCKET.value
        assert hook_context.store_type == StoreType.MEMORY.value

    @classmethod
    def test_is_frozen(cls, hook_context: HookContext) -> None:
        """HookContext should be immutable (i.e., frozen)."""
        with pytest.raises(FrozenInstanceError):
            cast("Any", hook_context).key = "new_key"

        with pytest.raises(FrozenInstanceError):
            cast("Any", hook_context).cost = 5


class TestHook:
    @classmethod
    def test_is_abstract(cls) -> None:
        """Hook should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            cast("type[object]", Hook)()

    @classmethod
    def test_must_implement_on_limit(cls) -> None:
        """Custom hook without on_limit implementation should raise TypeError."""

        class IncompleteHook(Hook):
            pass

        with pytest.raises(TypeError, match="abstract"):
            cast("type[object]", IncompleteHook)()

    @classmethod
    def test_on_limit__observe_result(cls) -> None:
        """Hook should be able to observe and act on rate limit result."""
        alert_calls: list[str] = []

        class AlertHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                context: HookContext = args[1]
                result: RateLimitResult = call_next()
                if result.limited:
                    alert_calls.append(context.key)
                return result

        hook: AlertHook = AlertHook()
        context: HookContext = HookContext(
            key="denied_key",
            cost=1,
            algorithm=RateLimiterType.GCRA.value,
            store_type=StoreType.MEMORY.value,
        )

        # Test with allowed result
        allowed_result: RateLimitResult = RateLimitResult(
            limited=False, state_values=(100, 99, 60.0, 0.0)
        )
        hook.on_limit(lambda: allowed_result, context)
        assert alert_calls == []

        # Test with denied result
        denied_result: RateLimitResult = RateLimitResult(
            limited=True, state_values=(100, 0, 60.0, 10.0)
        )
        hook.on_limit(lambda: denied_result, context)
        assert alert_calls == ["denied_key"]


class TestBuildHookChain:
    @classmethod
    def test_build_hook_chain__empty_hooks(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Empty hooks list should return do_limit directly."""

        def do_limit() -> RateLimitResult:
            return rate_limit_result

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [], do_limit, hook_context
        )
        assert chain is do_limit

    @classmethod
    def test_on_limit__exception_skips_hook(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Hook that raises exception should be skipped, chain continues."""
        call_order: list[str] = []

        class FailingHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_order.append("failing_before")
                raise RuntimeError("Hook failed!")

        class WorkingHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                call_order.append("working_before")
                res: RateLimitResult = call_next()
                call_order.append("working_after")
                return res

        def do_limit() -> RateLimitResult:
            call_order.append("do_limit")
            return rate_limit_result

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [FailingHook(), WorkingHook()], do_limit, hook_context
        )
        chain_result: RateLimitResult = chain()

        assert chain_result == rate_limit_result
        assert call_order == [
            "failing_before",
            "working_before",
            "do_limit",
            "working_after",
        ]

    @classmethod
    def test_on_limit__exception_logs_error(
        cls,
        hook_context: HookContext,
        rate_limit_result: RateLimitResult,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Hook exception should be logged with logger.exception."""

        class FailingHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                raise RuntimeError("Hook failed!")

        def do_limit() -> RateLimitResult:
            return rate_limit_result

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [FailingHook()], do_limit, hook_context
        )
        with caplog.at_level(logging.ERROR, logger="throttled.hooks"):
            chain()

        assert len(caplog.records) == 1
        assert "Hook" in caplog.records[0].message
        assert "raised during on_limit" in caplog.records[0].message
        assert caplog.records[0].exc_info is not None

    @classmethod
    def test_on_limit__multi_hooks(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Multiple hooks should execute in correct order (middleware pattern)."""
        call_order: list[str] = []

        class HookA(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                call_order.append("A_before")
                res: RateLimitResult = call_next()
                call_order.append("A_after")
                return res

        class HookB(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                call_order.append("B_before")
                res: RateLimitResult = call_next()
                call_order.append("B_after")
                return res

        def do_limit() -> RateLimitResult:
            call_order.append("do_limit")
            return rate_limit_result

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [HookA(), HookB()], do_limit, hook_context
        )
        chain()

        assert call_order == ["A_before", "B_before", "do_limit", "B_after", "A_after"]

    @classmethod
    def test_on_limit__exactly_once_invocation(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Hook that raises AFTER call_next() should not cause double execution.

        hook calls call_next() successfully, then raises during post-processing.
        The except block should return the cached result instead of calling next_fn()
        again.
        """
        call_count: int = 0

        class PostProcessFailHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                call_next()
                raise RuntimeError("post-processing failed")

        def do_limit() -> RateLimitResult:
            nonlocal call_count
            call_count += 1
            return rate_limit_result

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [PostProcessFailHook()], do_limit, hook_context
        )
        result: RateLimitResult = chain()

        assert result == rate_limit_result
        assert call_count == 1, f"do_limit called {call_count} times, expected 1"

    @classmethod
    def test_on_limit__next_fn_raises_before_except_fallback(
        cls, hook_context: HookContext
    ) -> None:
        """When next_fn() raises inside tracked_next (before except fallback),
        the exception should propagate."""

        class PassthroughHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], RateLimitResult] = args[0]
                return call_next()

        def do_limit() -> RateLimitResult:
            raise RuntimeError("store connection failed")

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [PassthroughHook()], do_limit, hook_context
        )
        with pytest.raises(RuntimeError, match="store connection failed"):
            chain()

    @classmethod
    def test_on_limit__next_fn_raises_after_except_fallback(
        cls, hook_context: HookContext
    ) -> None:
        """When hook raises BEFORE call_next() and the except fallback
        calls next_fn() which also raises, that exception should propagate."""

        class FailBeforeCallNextHook(Hook):
            def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                raise RuntimeError("hook failed before call_next")

        def do_limit() -> RateLimitResult:
            raise RuntimeError("store connection failed")

        chain: Callable[[], RateLimitResult] = build_hook_chain(
            [FailBeforeCallNextHook()], do_limit, hook_context
        )
        with pytest.raises(RuntimeError, match="store connection failed"):
            chain()


class _SyncNoopHook(Hook):
    def on_limit(
        self,
        call_next: Callable[[], RateLimitResult],
        context: HookContext,
    ) -> RateLimitResult:
        return call_next()


class _AsyncNoopHook(AsyncHook):
    async def on_limit(
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context: HookContext,
    ) -> RateLimitResult:
        return await call_next()


class _NotAHook:
    pass


class TestHookTypeValidation:
    @classmethod
    def test_validate_hooks__rejects_non_hook(cls) -> None:
        with pytest.raises(TypeError):
            Throttled(
                key="k",
                quota=per_sec(1),
                hooks=cast("list[Hook]", [_NotAHook()]),
            )

    @classmethod
    def test_validate_hooks__rejects_async_hook(cls) -> None:
        with pytest.raises(TypeError):
            Throttled(
                key="k",
                quota=per_sec(1),
                hooks=cast("list[Hook]", [_AsyncNoopHook()]),
            )


class TestHookContainerBehavior:
    @classmethod
    def test_validate_hooks__stores_as_tuple_from_list(cls) -> None:
        hooks = [_SyncNoopHook(), _SyncNoopHook()]
        throttle = Throttled(key="k", quota=per_sec(1), hooks=hooks)

        assert isinstance(throttle._hooks, tuple)
        assert throttle._hooks == tuple(hooks)

    @classmethod
    def test_validate_hooks__stores_as_tuple_from_tuple(cls) -> None:
        hooks = (_SyncNoopHook(), _SyncNoopHook())
        throttle = Throttled(key="k", quota=per_sec(1), hooks=hooks)

        assert isinstance(throttle._hooks, tuple)
        assert throttle._hooks == hooks
