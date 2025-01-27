from enum import Enum


class StoreType(Enum):
    REDIS: str = "redis"
    MEMORY: str = "memory"
