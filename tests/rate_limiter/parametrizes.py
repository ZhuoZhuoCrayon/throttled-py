import pytest

from throttled import per_min

LIMIT_C_QUOTA = pytest.mark.parametrize(
    "quota",
    [per_min(1, 1), per_min(10, 10), per_min(100, 100), per_min(1_000, 1_000)],
)

LIMIT_C_REQUESTS_NUM = pytest.mark.parametrize("requests_num", [10, 100, 1_000, 10_000])
