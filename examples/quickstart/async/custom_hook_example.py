import asyncio
import time
from collections.abc import Awaitable, Callable

from throttled.asyncio import Hook, HookContext, RateLimitResult, Throttled, per_sec


class TimingHook(Hook):
    async def on_limit(  # noqa: PLR6301
        self,
        call_next: Callable[[], Awaitable[RateLimitResult]],
        context: HookContext,
    ) -> RateLimitResult:
        start = time.perf_counter()
        result = await call_next()
        duration = time.perf_counter() - start

        print(f"Rate limit check took {duration:.4f}s")
        return result


throttle = Throttled(
    key="/api/users",
    quota=per_sec(10),
    hooks=[TimingHook()],
)


async def main():
    result = await throttle.limit()
    print(f"limited={result.limited}")


if __name__ == "__main__":
    asyncio.run(main())
