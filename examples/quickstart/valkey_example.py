from throttled import RateLimiterType, Throttled, store


@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota="1/m",
    # 🌟 use ValkeyStore as storage
    store=store.ValkeyStore(
        server="valkey://127.0.0.1:6379/0",
        # Sentinel mode
        # server="valkey+sentinel://:yourpassword@host1:26379,host2:26379/mymaster"
        # Cluster mode
        # server="valkey+cluster://:yourpassword@host1:6379,host2:6379"
        # 🌟 Pass any extra kwargs for the redis-py client.
        options={"REDIS_CLIENT_KWARGS": {}, "CONNECTION_POOL_KWARGS": {}},
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
