from collections.abc import Callable

from throttled import Hook, HookContext, RateLimitResult, Throttled, per_sec


class LoggingHook(Hook):
    def on_limit(  # noqa: PLR6301
        self,
        call_next: Callable[[], RateLimitResult],
        context: HookContext,
    ) -> RateLimitResult:
        # Before rate limit check
        print(f"Checking rate limit for {context.key}")

        # Execute rate limit check
        result = call_next()

        # After rate limit check
        status = "denied" if result.limited else "allowed"
        print(f"[{context.key}] {status} - remaining: {result.state.remaining}")

        return result


hook = LoggingHook()
throttle = Throttled(
    key="/api/users",
    quota=per_sec(10),
    hooks=[hook],
)


def main():
    result = throttle.limit()
    # Output:
    # Checking rate limit for /api/users
    # [/api/users] allowed - remaining: 9
    print(f"limited={result.limited}")


if __name__ == "__main__":
    main()
