import asyncio
from collections.abc import Awaitable, Callable

import pytest
from throttled.asyncio import Throttled, per_sec, store
from throttled.asyncio.hooks import Hook, build_hook_chain
from throttled.hooks import HookContext
from throttled.rate_limiter import RateLimitResult

WORKERS = 32
BATCH = 1_000


class CountingHook(Hook):
    """Hook that counts invocations."""

    def __init__(self):
        self.call_count = 0

    async def on_limit(
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context,
    ) -> RateLimitResult:
        self.call_count += 1
        return await call_next()


class PostProcessFailHook(Hook):
    """Hook that raises AFTER call_next() — triggers the fixed bug path."""

    def __init__(self):
        self.call_count = 0

    async def on_limit(
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context,
    ) -> RateLimitResult:
        self.call_count += 1
        await call_next()
        raise RuntimeError("post-processing failed")


@pytest.mark.asyncio
class TestHookConcurrent:
    @classmethod
    async def test_noop_hook__concurrent_call_count(cls) -> None:
        """Hook call count must equal total limit() calls under concurrency."""
        hook = CountingHook()
        throttle = Throttled(
            key="concurrent-test",
            quota=per_sec(1_000_000),
            store=store.MemoryStore(),
            hooks=[hook],
        )

        sem = asyncio.Semaphore(WORKERS)

        async def task():
            async with sem:
                await throttle.limit()

        await asyncio.gather(*[task() for _ in range(BATCH)])

        assert (
            hook.call_count == BATCH
        ), f"Hook called {hook.call_count} times, expected {BATCH}"

    @classmethod
    async def test_post_process_fail_hook__no_double_execution(cls) -> None:
        """Even under concurrency, post-process failure must not double-execute.

        Tests at the build_hook_chain level to directly verify
        that do_limit is not called twice when a hook raises after call_next().
        """
        hook = PostProcessFailHook()
        do_limit_count = 0
        sentinel = RateLimitResult(limited=False, state_values=(100, 99, 60.0, 0.0))
        context = HookContext(
            key="k", cost=1, algorithm="token_bucket", store_type="memory"
        )

        async def do_limit() -> RateLimitResult:
            nonlocal do_limit_count
            do_limit_count += 1
            return sentinel

        sem = asyncio.Semaphore(WORKERS)

        async def task():
            async with sem:
                chain = build_hook_chain([hook], do_limit, context)
                await chain()

        await asyncio.gather(*[task() for _ in range(BATCH)])

        assert hook.call_count == BATCH
        assert do_limit_count == BATCH, (
            f"do_limit called {do_limit_count} times, expected {BATCH} "
            "(double execution detected)"
        )

    @classmethod
    async def test_multi_hooks__concurrent_order_integrity(cls) -> None:
        """Multiple hooks under concurrency must not corrupt each other's state."""
        hook_a = CountingHook()
        hook_b = CountingHook()

        throttle = Throttled(
            key="multi-hook-test",
            quota=per_sec(1_000_000),
            store=store.MemoryStore(),
            hooks=[hook_a, hook_b],
        )

        sem = asyncio.Semaphore(WORKERS)

        async def task():
            async with sem:
                await throttle.limit()

        await asyncio.gather(*[task() for _ in range(BATCH)])

        assert hook_a.call_count == BATCH
        assert hook_b.call_count == BATCH
