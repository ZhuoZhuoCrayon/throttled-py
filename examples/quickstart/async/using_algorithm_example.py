import asyncio

from throttled.asyncio import RateLimiterType, Throttled, rate_limiter


async def main():
    throttle = Throttled(
        # 🌟Specifying a current limiting algorithm
        using=RateLimiterType.FIXED_WINDOW.value,
        # using=RateLimiterType.SLIDING_WINDOW.value,
        # using=RateLimiterType.LEAKING_BUCKET.value,
        # using=RateLimiterType.TOKEN_BUCKET.value,
        # using=RateLimiterType.GCRA.value,
        quota=rate_limiter.per_min(1),
    )
    assert (await throttle.limit("key", 2)).limited


if __name__ == "__main__":
    asyncio.run(main())
