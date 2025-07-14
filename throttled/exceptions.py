from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from throttled.rate_limiter import RateLimitResult


class BaseThrottledError(Exception):
    """Base class for all throttled-related exceptions."""

    pass


class SetUpError(BaseThrottledError):
    """Exception raised when there is an error during setup."""

    pass


class DataError(BaseThrottledError):
    """Exception raised for errors related to data integrity or format.

    Thrown when the parameter is invalid, such as: Invalid key: None,
    must be a non-empty key.
    """

    pass


class StoreUnavailableError(BaseThrottledError):
    """Exception raised when the store (e.g., Redis) is unavailable."""

    pass


class LimitedError(BaseThrottledError):
    """Exception raised when a rate limit is exceeded.

    When a request is throttled, an exception is thrown, such as:
    Rate limit exceeded: remaining=0, reset_after=60, retry_after=60.
    """

    def __init__(self, rate_limit_result: Optional["RateLimitResult"] = None):
        self.rate_limit_result: Optional["RateLimitResult"] = rate_limit_result
        if not self.rate_limit_result or not self.rate_limit_result.state:
            message: str = "Rate limit exceeded."
        else:
            message: str = (
                "Rate limit exceeded: remaining={remaining}, "
                "reset_after={reset_after}, retry_after={retry_after}."
            ).format(
                remaining=self.rate_limit_result.state.remaining,
                reset_after=self.rate_limit_result.state.reset_after,
                retry_after=self.rate_limit_result.state.retry_after,
            )
        super().__init__(message)
