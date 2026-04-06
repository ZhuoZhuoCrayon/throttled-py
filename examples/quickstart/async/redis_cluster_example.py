import asyncio

from throttled.asyncio import RateLimiterType, Throttled, store


@Throttled(
    key="/api/products",
    using=RateLimiterType.TOKEN_BUCKET.value,
    quota="1/m",
    # 🌟 use RedisStore as storage
    store=store.RedisStore(
        server="redis+cluster://:yourpassword@host1:6379,host2:6379",
        # 🌟 Pass any extra kwargs for redis-py Cluster client
        options={"REDIS_CLIENT_KWARGS": {}},
    ),
)
async def products() -> list[dict[str, str]]:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


async def demo() -> None:
    await products()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    await products()


if __name__ == "__main__":
    asyncio.run(demo())
