from throttled import RateLimiterType, Throttled, rate_limiter, store

throttle = Throttled(
    # 🌟指定限流算法
    using=RateLimiterType.FIXED_WINDOW.value,
    quota=rate_limiter.per_min(1),
    store=store.MemoryStore(),
)
assert throttle.limit("key", 2).limited is True
