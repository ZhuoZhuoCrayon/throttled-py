from throttled import Throttled, exceptions, rate_limiter


def call_api():
    print("doing something...")


def main():
    throttle: Throttled = Throttled(key="/api/v1/users/", quota=rate_limiter.per_min(1))
    with throttle as result:
        # The first call will not be rate limited.
        assert not result.limited
        # Get the state of the rate limiter:
        # >> RateLimitState(limit=1, remaining=0, reset_after=60, retry_after=0)
        print(result.state)

        call_api()

    try:
        with throttle:
            call_api()
    except exceptions.LimitedError as exc:
        # >> Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
        print(exc)


if __name__ == "__main__":
    main()
