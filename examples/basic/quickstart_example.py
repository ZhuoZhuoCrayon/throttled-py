from throttled import RateLimiterType, Throttled, rate_limter, store, utils

throttle = Throttled(
    # 📈 使用令牌桶作为限流算法。
    using=RateLimiterType.TOKEN_BUCKET.value,
    # 🪣 设置配额：每秒填充 1_000 个 Token（limit），桶大小为 1_000（burst）。
    quota=rate_limter.per_sec(1_000, burst=1_000),
    # 📁 使用内存作为存储
    store=store.MemoryStore(),
)


def call_api() -> bool:
    # 💧消耗 Key=/ping 的一个 Token。
    result = throttle.limit("/ping", cost=1)
    return result.limited


if __name__ == "__main__":
    # ✅ Total: 100000, 🕒 Latency: 0.5463 ms/op, 🚀 Throughput: 55630 req/s (--)
    # ❌ Denied: 96314 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.concurrent(call_api, 100_000, workers=32))
    print(f"❌ Denied: {denied_num} requests")
