from enum import Enum

from .types import RateLimiterTypeT


class StoreType(Enum):
    REDIS: str = "redis"
    MEMORY: str = "memory"


class StoreTTLState(Enum):
    NOT_TTL: int = -1
    NOT_EXIST: int = -2


class RateLimiterType(Enum):
    FIXED_WINDOW: RateLimiterTypeT = "fixed_window"
    SLIDING_WINDOW: RateLimiterTypeT = "sliding_window"
    LEAKING_BUCKET: RateLimiterTypeT = "leaking_bucket"
    TOKEN_BUCKET: RateLimiterTypeT = "token_bucket"
    GCRA: RateLimiterTypeT = "gcra"
