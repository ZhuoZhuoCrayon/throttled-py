from enum import Enum
from typing import List

from .types import AtomicActionTypeT, RateLimiterTypeT


class StoreType(Enum):
    REDIS: str = "redis"
    MEMORY: str = "memory"

    @classmethod
    def choice(cls) -> List[str]:
        return [cls.REDIS.value, cls.MEMORY.value]


STORE_TTL_STATE_NOT_TTL: int = -1
STORE_TTL_STATE_NOT_EXIST: int = -2

# Enumeration for types of AtomicActions
ATOMIC_ACTION_TYPE_LIMIT: AtomicActionTypeT = "limit"
ATOMIC_ACTION_TYPE_PEEK: AtomicActionTypeT = "peek"


class RateLimiterType(Enum):
    FIXED_WINDOW: RateLimiterTypeT = "fixed_window"
    SLIDING_WINDOW: RateLimiterTypeT = "sliding_window"
    LEAKING_BUCKET: RateLimiterTypeT = "leaking_bucket"
    TOKEN_BUCKET: RateLimiterTypeT = "token_bucket"
    GCRA: RateLimiterTypeT = "gcra"

    @classmethod
    def choice(cls) -> List[RateLimiterTypeT]:
        return [
            cls.FIXED_WINDOW.value,
            cls.SLIDING_WINDOW.value,
            cls.LEAKING_BUCKET.value,
            cls.TOKEN_BUCKET.value,
            cls.GCRA.value,
        ]
