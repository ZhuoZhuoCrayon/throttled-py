from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from throttled.rate_limiter import RateLimitResult


class BaseThrottledError(Exception):
    """Base class for all throttled-related exceptions."""


class SetUpError(BaseThrottledError):
    """Exception raised when there is an error during setup."""


class DataError(BaseThrottledError):
    """Exception raised for errors related to data integrity or format.

    Thrown when the parameter is invalid, such as: Invalid key: None,
    must be a non-empty key.
    """


class StoreUnavailableError(BaseThrottledError):
    """Exception raised when the store (e.g., Redis) is unavailable."""


class LimitedError(BaseThrottledError):
    """Exception raised when a rate limit is exceeded.

    When a request is throttled, an exception is thrown, such as:
    Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    """

    def __init__(self, rate_limit_result: Optional["RateLimitResult"] = None) -> None:
        #: The result after executing the RateLimiter for the given key.
        self.rate_limit_result: RateLimitResult | None = rate_limit_result
        if not self.rate_limit_result or not self.rate_limit_result.state:
            super().__init__("Rate limit exceeded.")
        else:
            super().__init__(
                "Rate limit exceeded: "
                f"remaining={self.rate_limit_result.state.remaining}, "
                f"reset_after={self.rate_limit_result.state.reset_after}, "
                f"retry_after={self.rate_limit_result.state.retry_after}."
            )
