"""FastAPI integration for throttled-py."""

from .exceptions import RateLimitExceededError, rate_limit_exceeded_handler
from .headers import RateLimitContext, RateLimitHeaderPolicy
from .key_funcs import get_remote_address
from .limiter import KeyFunc, Limiter
from .middleware import RateLimitMiddleware

__all__ = [
    "KeyFunc",
    "Limiter",
    "RateLimitContext",
    "RateLimitExceededError",
    "RateLimitHeaderPolicy",
    "RateLimitMiddleware",
    "get_remote_address",
    "rate_limit_exceeded_handler",
]
