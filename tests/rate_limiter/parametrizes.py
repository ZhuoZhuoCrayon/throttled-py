from typing import Any, Dict, List

import pytest

from throttled import per_min

LIMIT_C_QUOTA = pytest.mark.parametrize(
    "quota",
    [per_min(1, 1), per_min(10, 10), per_min(100, 100), per_min(1_000, 1_000)],
)

LIMIT_C_REQUESTS_NUM = pytest.mark.parametrize("requests_num", [10, 100, 1_000, 10_000])


FIXED_WINDOW_LIMIT_CASES: List[Dict[str, Any]] = [
    {"cost": 0, "limited": False, "remaining": 5, "count": 0},
    {"cost": 1, "limited": False, "remaining": 4, "count": 1},
    {"cost": 4, "limited": False, "remaining": 0, "count": 5},
    {"cost": 4, "limited": True, "remaining": 0, "count": 9},
    {"cost": 0, "limited": False, "remaining": 0, "count": 9},
]

GCRA_LIMIT_CASES: List[Dict[str, Any]] = [
    {"cost": 0, "limited": False, "remaining": 10},
    {"cost": 1, "limited": False, "remaining": 9},
    {"cost": 5, "limited": False, "remaining": 5, "sleep": 1},
    {"cost": 5, "limited": False, "remaining": 0},
    {"cost": 1, "limited": True, "remaining": 0},
    {"cost": 0, "limited": False, "remaining": 0},
]

LEAKING_BUCKET_LIMIT_CASES: List[Dict[str, Any]] = [
    {"cost": 0, "limited": False, "remaining": 10},
    {"cost": 1, "limited": False, "remaining": 9},
    {"cost": 10, "limited": True, "remaining": 9, "retry_after": 1},
    {"cost": 5, "limited": False, "remaining": 5, "sleep": 1},
    {"cost": 8, "limited": True, "remaining": 5, "retry_after": 3},
    {"cost": 5, "limited": False, "remaining": 0},
    {"cost": 1, "limited": True, "remaining": 0, "retry_after": 1},
    {"cost": 0, "limited": False, "remaining": 0},
]

TOKEN_BUCKET_LIMIT_CASES: List[Dict[str, Any]] = LEAKING_BUCKET_LIMIT_CASES

SLIDING_WINDOW_LIMIT_CASES: List[Dict[str, Any]] = [
    {"cost": 0, "limited": False, "remaining": 5, "count": 0, "ttl": 3 * 60},
    {"cost": 1, "limited": False, "remaining": 4, "count": 1},
    {"cost": 4, "limited": False, "remaining": 0, "count": 5},
    {"cost": 4, "limited": True, "remaining": 0, "count": 5},
    {"cost": 0, "limited": False, "remaining": 0, "count": 5},
]
