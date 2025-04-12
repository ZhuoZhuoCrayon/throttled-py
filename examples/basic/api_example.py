from throttled import Throttled

# 参数全部缺省时，默认初始化一个基于「内存」、每分钟允许通过 60 个请求、使用「令牌桶算法」的限流器。
throttle = Throttled()

# 消耗 1 次请求，输出：RateLimitResult(limited=False,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0))
print(throttle.limit("key", 1))
# 获取限流器状态，输出：RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=0)
print(throttle.peek("key"))

# 消耗 60 次请求，触发限流，输出：RateLimitResult(limited=True,
# state=RateLimitState(limit=60, remaining=59, reset_after=1, retry_after=60))
print(throttle.limit("key", 60))
