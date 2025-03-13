from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from throttled.rate_limter import RateLimitResult


class BaseThrottledError(Exception):
    pass


class SetUpError(BaseThrottledError):
    pass


class DataError(BaseThrottledError):
    pass


class StoreUnavailableError(BaseThrottledError):
    pass


class LimitedError(BaseThrottledError):
    def __init__(self, rate_limit_result: Optional["RateLimitResult"] = None):
        self.rate_limit_result: Optional["RateLimitResult"] = rate_limit_result
        if not self.rate_limit_result or not self.rate_limit_result.state:
            message: str = "Rate limit exceeded"
        else:
            message: str = (
                "Rate limit exceeded: remaining={remaining}, "
                "reset_after={reset_after}"
            ).format(
                remaining=self.rate_limit_result.state.remaining,
                reset_after=self.rate_limit_result.state.reset_after,
            )
        super().__init__(message)
