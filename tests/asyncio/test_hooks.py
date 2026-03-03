from collections.abc import Awaitable, Callable

import pytest
from throttled import (
    HookContext,
    RateLimiterType,
    RateLimitResult,
)
from throttled.asyncio.hooks import Hook, build_hook_chain
from throttled.constants import StoreType


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


class TestHook:
    @classmethod
    def test_is_abstract(cls) -> None:
        """Hook should not be instantiable directly."""
        with pytest.raises(TypeError, match="abstract"):
            Hook()

    @classmethod
    def test_must_implement_on_limit(cls) -> None:
        """Custom hook without on_limit implementation should raise TypeError."""

        class IncompleteHook(Hook):
            pass

        with pytest.raises(TypeError, match="abstract"):
            IncompleteHook()

    @classmethod
    @pytest.mark.asyncio
    async def test_on_limit__observe_result(cls) -> None:
        """Hook should be able to observe and act on rate limit result."""
        alert_calls: list[str] = []

        class AlertHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                context: HookContext = args[1]
                result: RateLimitResult = await call_next()
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

        async def return_allowed():
            return allowed_result

        await hook.on_limit(return_allowed, context)
        assert alert_calls == []

        # Test with denied result
        denied_result: RateLimitResult = RateLimitResult(
            limited=True, state_values=(100, 0, 60.0, 10.0)
        )

        async def return_denied():
            return denied_result

        await hook.on_limit(return_denied, context)
        assert alert_calls == ["denied_key"]


@pytest.mark.asyncio
class TestBuildHookChain:
    @classmethod
    async def test_build_hook_chain__empty_hooks(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Empty hooks list should return do_limit directly."""

        async def do_limit() -> RateLimitResult:
            return rate_limit_result

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [], do_limit, hook_context
        )
        assert chain is do_limit

    @classmethod
    async def test_on_limit__exception_skips_hook(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Hook that raises exception should be skipped, chain continues."""
        call_order: list[str] = []

        class FailingHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_order.append("failing_before")
                raise RuntimeError("Hook failed!")

        class WorkingHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                call_order.append("working_before")
                res: RateLimitResult = await call_next()
                call_order.append("working_after")
                return res

        async def do_limit() -> RateLimitResult:
            call_order.append("do_limit")
            return rate_limit_result

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [FailingHook(), WorkingHook()], do_limit, hook_context
        )
        chain_result: RateLimitResult = await chain()

        assert chain_result == rate_limit_result
        assert call_order == [
            "failing_before",
            "working_before",
            "do_limit",
            "working_after",
        ]

    @classmethod
    async def test_on_limit__multi_hooks(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Multiple hooks should execute in correct order (middleware pattern)."""
        call_order: list[str] = []

        class HookA(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                call_order.append("A_before")
                res: RateLimitResult = await call_next()
                call_order.append("A_after")
                return res

        class HookB(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                call_order.append("B_before")
                res: RateLimitResult = await call_next()
                call_order.append("B_after")
                return res

        async def do_limit() -> RateLimitResult:
            call_order.append("do_limit")
            return rate_limit_result

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [HookA(), HookB()], do_limit, hook_context
        )
        await chain()

        assert call_order == ["A_before", "B_before", "do_limit", "B_after", "A_after"]

    @classmethod
    async def test_on_limit__exactly_once_invocation(
        cls, hook_context: HookContext, rate_limit_result: RateLimitResult
    ) -> None:
        """Hook that raises AFTER await call_next() should not cause double execution.

        hook calls call_next() successfully, then raises during post-processing.
        The except block should return the cached result instead of calling next_fn() again.
        """
        call_count: int = 0

        class PostProcessFailHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                await call_next()
                raise RuntimeError("post-processing failed")

        async def do_limit() -> RateLimitResult:
            nonlocal call_count
            call_count += 1
            return rate_limit_result

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [PostProcessFailHook()], do_limit, hook_context
        )
        result: RateLimitResult = await chain()

        assert result == rate_limit_result
        assert call_count == 1, f"do_limit called {call_count} times, expected 1"

    @classmethod
    async def test_on_limit__next_fn_raises_before_except_fallback(
        cls, hook_context: HookContext
    ) -> None:
        """When next_fn() raises inside tracked_next (before except fallback),
        the exception should propagate."""

        class PassthroughHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                call_next: Callable[[], Awaitable[RateLimitResult]] = args[0]
                return await call_next()

        async def do_limit() -> RateLimitResult:
            raise RuntimeError("store connection failed")

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [PassthroughHook()], do_limit, hook_context
        )
        with pytest.raises(RuntimeError, match="store connection failed"):
            await chain()

    @classmethod
    async def test_on_limit__next_fn_raises_after_except_fallback(
        cls, hook_context: HookContext
    ) -> None:
        """When hook raises BEFORE call_next() and the except fallback
        calls next_fn() which also raises, that exception should propagate."""

        class FailBeforeCallNextHook(Hook):
            async def on_limit(self, *args, **kwargs) -> RateLimitResult:  # noqa: PLR6301
                raise RuntimeError("hook failed before call_next")

        async def do_limit() -> RateLimitResult:
            raise RuntimeError("store connection failed")

        chain: Callable[[], Awaitable[RateLimitResult]] = build_hook_chain(
            [FailBeforeCallNextHook()], do_limit, hook_context
        )
        with pytest.raises(RuntimeError, match="store connection failed"):
            await chain()
