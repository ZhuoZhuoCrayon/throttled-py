"""FastAPI integration for throttled-py."""

from .exceptions import RateLimitExceededError, rate_limit_exceeded_handler
from .key_funcs import get_remote_address
from .limiter import KeyFunc, Limiter
from .middleware import RateLimitMiddleware

__all__ = [
    "KeyFunc",
    "Limiter",
    "RateLimitExceededError",
    "RateLimitMiddleware",
    "get_remote_address",
    "rate_limit_exceeded_handler",
]
