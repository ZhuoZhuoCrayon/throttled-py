import asyncio

from throttled.asyncio import RateLimiterType, Throttled, store


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
async def products() -> list[dict[str, str]]:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


async def demo() -> None:
    await products()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    await products()


if __name__ == "__main__":
    asyncio.run(demo())
