from throttled import Throttled, exceptions, rate_limiter


# 创建一个每分钟允许通过 1 次的限流器。
@Throttled(key="/ping", quota=rate_limiter.per_min(1))
def ping() -> str:
    return "ping"


ping()
try:
    ping()  # 当触发限流时，抛出 LimitedError。
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
