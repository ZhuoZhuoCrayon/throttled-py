import asyncio

from throttled.asyncio import Throttled, rate_limiter, store

# 🌟 Use MemoryStore as the storage backend.
mem_store = store.MemoryStore()


@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
async def ping() -> str:
    return "ping"


@Throttled(key="ping-pong", quota=rate_limiter.per_min(1), store=mem_store)
async def pong() -> str:
    return "pong"


async def demo():
    # >> ping
    await ping()
    # >> throttled.exceptions.LimitedError:
    # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    await pong()


if __name__ == "__main__":
    asyncio.run(demo())
