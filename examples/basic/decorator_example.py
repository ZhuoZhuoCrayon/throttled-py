from throttled import Throttled, exceptions, rate_limter


# 创建一个每秒允许通过 1 次的限流器。
@Throttled(key="/ping", quota=rate_limter.per_min(1))
def ping() -> str:
    return "ping"


def demo():
    ping()
    try:
        ping()  # 当触发限流时，抛出 LimitedError。
    except exceptions.LimitedError as exc:
        print(exc)  # Rate limit exceeded: remaining=0, reset_after=60
        # 在异常中获取限流结果：RateLimitResult(limited=True,
        # state=RateLimitState(limit=1, remaining=0, reset_after=60))
        print(exc.rate_limit_result)


if __name__ == "__main__":
    demo()
