from datetime import timedelta

from throttled import rate_limter
from throttled.rate_limter import Quota, Rate

# 60 / s
rate_limter.per_sec(60)
# 60 / min
rate_limter.per_min(60)
# 60 / h
rate_limter.per_hour(60)
# 60 / d
rate_limter.per_day(60)

# 允许突发处理 120 个请求
# 未指定 burst 时，默认设置为 limit 传入值
rate_limter.per_min(60, burst=120)

# 两分钟一共允许 120 个请求，允许突发处理 150 个请求
Quota(Rate(period=timedelta(minutes=2), limit=120), burst=150)
