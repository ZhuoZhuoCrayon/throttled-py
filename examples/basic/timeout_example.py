from throttled import RateLimiterType, Throttled, rate_limiter, utils

throttle = Throttled(
    using=RateLimiterType.GCRA.value,
    quota=rate_limiter.per_sec(100, burst=100),
    # ⏳ 设置超时时间为 1 秒，表示允许等待重试，等待时间超过 1 秒返回最后一次限流结果。
    timeout=1,
)


def call_api() -> bool:
    # ⬆️⏳ 函数调用传入 timeout 将覆盖全局设置的 timeout。
    result = throttle.limit("/ping", cost=1, timeout=1)
    return result.limited


if __name__ == "__main__":
    # 👇 实际 QPS 接近预设容量（100 req/s）：
    # ✅ Total: 1000, 🕒 Latency: 35.8103 ms/op, 🚀 Throughput: 111 req/s (--)
    # ❌ Denied: 8 requests
    benchmark: utils.Benchmark = utils.Benchmark()
    denied_num: int = sum(benchmark.concurrent(call_api, 1_000, workers=4))
    print(f"❌ Denied: {denied_num} requests")
