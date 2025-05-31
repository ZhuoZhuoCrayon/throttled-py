from throttled import Throttled, exceptions, rate_limiter


# 创建一个每分钟允许通过 1 次的限流器。
@Throttled(key="/ping", quota=rate_limiter.per_min(1))
def ping() -> str:
    return "ping"


# 创建一个每分钟允许通过 2 个 cost 的限流器，每次调用消耗 2 个 cost
@Throttled(key="/heavy_ping", quota=rate_limiter.per_min(2), cost=2)
def heavy_ping() -> str:
    return "heavy ping"


# 创建一个异步的限流器示例
@Throttled(key="/async_ping", quota=rate_limiter.per_min(1), cost=1)
async def async_ping() -> str:
    return "async ping"


if __name__ == "__main__":
    # 同步函数示例
    # 第一次调用成功
    print(ping())  # 输出: ping
    try:
        # 第二次调用会被限流
        print(ping())
    except exceptions.LimitedError:
        print("Rate limited!")  # 输出: Rate limited!

    # 第一次调用成功，但会消耗 2 个 cost
    print(heavy_ping())  # 输出: heavy ping
    try:
        # 第二次调用会被限流，因为配额只有 2，而每次调用消耗 2 个 cost
        print(heavy_ping())
    except exceptions.LimitedError:
        print("Rate limited!")  # 输出: Rate limited!

    # 异步函数示例
    import asyncio

    async def main():
        # 第一次调用成功
        print(await async_ping())  # 输出: async ping
        try:
            # 第二次调用会被限流
            print(await async_ping())
        except exceptions.LimitedError:
            print("Async rate limited!")  # 输出: Async rate limited!

    # 运行异步示例
    asyncio.run(main())
