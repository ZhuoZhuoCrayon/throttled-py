from datetime import timedelta

from throttled import rate_limiter

rate_limiter.per_sec(60)  # 60 req/sec
rate_limiter.per_min(60)  # 60 req/min
rate_limiter.per_hour(60)  # 60 req/hour
rate_limiter.per_day(60)  # 60 req/day
rate_limiter.per_week(60)  # 60 req/week

# 允许突发处理 120 个请求。
# 未指定 burst 时，默认设置为 limit 传入值。
rate_limiter.per_min(60, burst=120)

# 两分钟一共允许 120 个请求，允许突发处理 150 个请求。
rate_limiter.per_duration(timedelta(minutes=2), limit=120, burst=150)
