from datetime import timedelta

from throttled import rate_limiter
from throttled.rate_limiter import Quota, Rate

rate_limiter.per_sec(60)  # 60 / sec
rate_limiter.per_min(60)  # 60 / min
rate_limiter.per_hour(60)  # 60 / hour
rate_limiter.per_day(60)  # 60 / day

# 允许突发处理 120 个请求
# 未指定 burst 时，默认设置为 limit 传入值
rate_limiter.per_min(60, burst=120)

# 两分钟一共允许 120 个请求，允许突发处理 150 个请求
Quota(Rate(period=timedelta(minutes=2), limit=120), burst=150)
