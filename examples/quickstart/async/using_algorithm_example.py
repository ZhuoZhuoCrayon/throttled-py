import asyncio

from throttled.asyncio import RateLimiterType, Throttled


async def main() -> None:
    throttle = Throttled(
        # 🌟Specifying a current limiting algorithm
        using=RateLimiterType.FIXED_WINDOW.value,
        # using=RateLimiterType.SLIDING_WINDOW.value,
        # using=RateLimiterType.LEAKING_BUCKET.value,
        # using=RateLimiterType.TOKEN_BUCKET.value,
        # using=RateLimiterType.GCRA.value,
        quota="1/m",
    )
    assert (await throttle.limit("key", 2)).limited


if __name__ == "__main__":
    asyncio.run(main())
