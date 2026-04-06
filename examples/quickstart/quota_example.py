from datetime import timedelta

from throttled import rate_limiter

# Built-in constructors for common fixed periods.
rate_limiter.per_sec(60)  # 60 req/sec
rate_limiter.per_min(60)  # 60 req/min
rate_limiter.per_hour(60)  # 60 req/hour
rate_limiter.per_day(60)  # 60 req/day
rate_limiter.per_week(60)  # 60 req/week

# Allow up to 120 requests as burst capacity.
# If burst is omitted, it defaults to the same value as limit.
rate_limiter.per_min(60, burst=120)

# Custom period example:
# allow 120 requests per 2 minutes, with burst capacity of 150.
rate_limiter.per_duration(timedelta(minutes=2), limit=120, burst=150)
