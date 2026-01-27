from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest
from throttled import (
    HookContext,
    RateLimiterType,
    RateLimitResult,
)
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
            hook_context.key = "new_key"

        with pytest.raises(FrozenInstanceError):
            hook_context.cost = 5


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
