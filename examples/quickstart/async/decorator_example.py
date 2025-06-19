import asyncio

from throttled.asyncio import Throttled, exceptions, rate_limiter

quota = rate_limiter.per_min(2)


# Create a rate limiter that allows 2 request per minute.
@Throttled(key="/ping", quota=quota)
async def ping() -> str:
    return "ping"


# Create a rate limiter that allows 2 cost per minute, consuming 2 Tokens per call.
@Throttled(key="/ping", quota=quota, cost=2)
async def heavy_ping() -> str:
    return "heavy_pong"


async def main():
    # The first call should succeed.
    # >> pong
    print(await ping())

    try:
        # The second call will be rate limited, because heavy_ping consumes 2 Tokens
        # and 1 Token has been consumed by the first call.
        await heavy_ping()
    except exceptions.LimitedError as exc:
        # >> Rate limit exceeded: remaining=1, reset_after=30, retry_after=60.
        print(exc)


if __name__ == "__main__":
    asyncio.run(main())
