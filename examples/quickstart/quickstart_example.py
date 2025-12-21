from throttled import RateLimiterType, Throttled, rate_limiter, utils

throttle = Throttled(
    # 📈 Use Token Bucket algorithm.
    using=RateLimiterType.TOKEN_BUCKET.value,
    # 🪣 Set quota: 1,000 tokens per second (limit), bucket size 1,000 (burst).
    quota=rate_limiter.per_sec(1_000, burst=1_000),
    # 📁 By default, global MemoryStore is used as the storage backend.
)


def call_api() -> bool:
    # 💧 Deduct 1 token for key="/ping"
    result = throttle.limit("/ping", cost=1)
    return result.limited


if __name__ == "__main__":
    # 💻 Python 3.12.10, Linux 5.4.119-1-tlinux4-0009.1, Arch: x86_64, Specs: 2C4G.
    # ✅ Total: 100000, 🕒 Latency: 0.0068 ms/op, 🚀 Throughput: 122513 req/s (--)
    # ❌ Denied: 98000 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.serial(call_api, 100_000))
    print(f"❌ Denied: {denied_num} requests")
