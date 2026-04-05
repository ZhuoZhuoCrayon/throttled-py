import asyncio

from throttled.asyncio import Throttled

throttle = Throttled(
    key="/api/ping",
    quota="100/s burst 200",
)


async def main() -> None:
    result = await throttle.limit()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
