import time
from collections.abc import Callable

from throttled import Hook, HookContext, RateLimitResult, Throttled, per_sec


class TimingHook(Hook):
    def on_limit(  # noqa: PLR6301
        self,
        call_next: Callable[[], RateLimitResult],
        context: HookContext,
    ) -> RateLimitResult:
        start = time.perf_counter()
        result = call_next()
        duration = time.perf_counter() - start

        print(f"Rate limit check took {duration:.4f}s")
        return result


throttle = Throttled(
    key="/api/users",
    quota=per_sec(10),
    hooks=[TimingHook()],
)


def main():
    result = throttle.limit()
    print(f"limited={result.limited}")


if __name__ == "__main__":
    main()
