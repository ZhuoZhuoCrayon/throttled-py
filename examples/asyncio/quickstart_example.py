import asyncio

from throttled.asyncio import RateLimiterType, Throttled, rate_limiter, store, utils

throttle = Throttled(
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limiter.per_sec(1_000, burst=1_000),
    store=store.MemoryStore(),
)


async def call_api() -> bool:
    result = await throttle.limit("/ping", cost=1)
    return result.limited


async def main():
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(await benchmark.async_serial(call_api, 100_000))
    print(f"❌ Denied: {denied_num} requests")


if __name__ == "__main__":
    asyncio.run(main())
