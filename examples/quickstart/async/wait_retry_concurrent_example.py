import asyncio

from throttled.asyncio import RateLimiterType, Throttled, rate_limiter, utils

throttle = Throttled(
    using=RateLimiterType.GCRA.value,
    quota=rate_limiter.per_sec(100, burst=100),
    # ⏳ Set timeout to 1 second, which allows waiting for retry,
    # and returns the last RateLimitResult if the wait exceeds 1 second.
    timeout=1,
)


async def call_api() -> bool:
    # ⬆️⏳ Function call with timeout will override the global timeout.
    result = await throttle.limit("/ping", cost=1, timeout=1)
    return result.limited


async def main():
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(await benchmark.async_concurrent(call_api, 1_000, workers=4))
    print(f"❌ Denied: {denied_num} requests")


if __name__ == "__main__":
    # 👇 The actual QPS is close to the preset quota (100 req/s):
    # ✅ Total: 1000, 🕒 Latency: 35.8103 ms/op, 🚀 Throughput: 111 req/s (--)
    # ❌ Denied: 8 requests
    asyncio.run(main())
