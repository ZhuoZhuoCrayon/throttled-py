import asyncio
import time

from throttled.asyncio import RateLimiterType, Throttled, rate_limiter


@Throttled(
    key="ping",
    using=RateLimiterType.GCRA.value,
    quota=rate_limiter.per_sec(2, burst=2),
    # ⏳ Set timeout to 0.5 second, which allows waiting for retry,
    # and returns the last RateLimitResult if the wait exceeds 0.5 second.
    timeout=0.5,
)
async def ping() -> str:
    return "pong"


async def main():
    # Make 5 sequential requests.
    start_time = time.time()
    for i in range(5):
        await ping()
        print(f"Request {i + 1} completed at {time.time() - start_time:.2f}s")

    print(f"\nTotal time for 5 requests at 2/sec: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
