from throttled import RateLimiterType, Throttled, rate_limiter


def main():
    throttle = Throttled(
        # 🌟Specifying a current limiting algorithm
        using=RateLimiterType.FIXED_WINDOW.value,
        # using=RateLimiterType.SLIDING_WINDOW.value,
        # using=RateLimiterType.LEAKING_BUCKET.value,
        # using=RateLimiterType.TOKEN_BUCKET.value,
        # using=RateLimiterType.GCRA.value,
        quota=rate_limiter.per_min(1),
    )
    assert throttle.limit("key", 2).limited


if __name__ == "__main__":
    main()
