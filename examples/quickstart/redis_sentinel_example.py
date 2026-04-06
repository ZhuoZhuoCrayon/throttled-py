from throttled import RateLimiterType, Throttled, store


@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota="1/m",
    # 🌟 use RedisStore as storage
    store=store.RedisStore(
        server="redis+sentinel://:yourpassword@host1:26379,host2:26379/mymaster",
        # 🌟 Pass any extra kwargs for redis-py Sentinel client.
        options={
            "SENTINEL_KWARGS": {},
            "REDIS_CLIENT_KWARGS": {},
            "CONNECTION_POOL_KWARGS": {},
        },
    ),
)
def products() -> list[dict[str, str]]:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


def demo() -> None:
    products()  # type: ignore[call-arg]
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    products()  # type: ignore[call-arg]


if __name__ == "__main__":
    demo()
