import asyncio

from throttled.asyncio import Throttled

throttle = Throttled(
    key="/api/ping",
    quota="100/s",
    # quota="100/s burst 200",
    # quota="100 per second",
    # quota="100 per second burst 200",
)


async def main() -> None:
    print(await throttle.limit())


if __name__ == "__main__":
    asyncio.run(main())
