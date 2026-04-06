import asyncio

from throttled.asyncio import Throttled


# 🌟 Use the global MemoryStore as the storage backend.
@Throttled(key="/api/products", quota="1/m")
async def products() -> list[dict[str, str]]:
    return [{"name": "iPhone"}, {"name": "MacBook"}]


async def demo() -> None:
    await products()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    await products()


if __name__ == "__main__":
    asyncio.run(demo())
