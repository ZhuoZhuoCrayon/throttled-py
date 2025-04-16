from throttled import Throttled, exceptions, rate_limiter


def call_api():
    print("doing something...")


throttle: Throttled = Throttled(key="/api/v1/users/", quota=rate_limiter.per_min(1))
with throttle as rate_limit_result:
    print(f"limited: {rate_limit_result.limited}")
    call_api()

try:
    with throttle:
        call_api()
except exceptions.LimitedError as exc:
    print(exc)  # Rate limit exceeded: remaining=0, reset_after=60, retry_after=60
