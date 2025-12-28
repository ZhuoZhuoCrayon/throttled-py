from throttled import RateLimiterType, Throttled, rate_limiter, store


@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota=rate_limiter.per_min(1),
    # 🌟 use RedisStore as storage
    store=store.RedisStore(
        server="redis://127.0.0.1:6379/0",
        # 🌟 Pass any extra kwargs for redis-py client.
        options={"REDIS_CLIENT_KWARGS": {}, "CONNECTION_POOL_KWARGS": {}},
    ),
)
def products() -> list:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


def demo():
    products()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    products()


if __name__ == "__main__":
    demo()
