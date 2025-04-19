from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import pytest

from throttled import Quota, rate_limter


class TestQuota:
    @pytest.mark.parametrize(
        "per_xx,constructor_kwargs,expect",
        [
            [rate_limter.per_sec, {"limit": 10}, {"limit": 10, "burst": 10, "sec": 1}],
            [rate_limter.per_min, {"limit": 10}, {"limit": 10, "burst": 10, "sec": 60}],
            [
                rate_limter.per_hour,
                {"limit": 10},
                {"limit": 10, "burst": 10, "sec": 3600},
            ],
            [
                rate_limter.per_day,
                {"limit": 10},
                {"limit": 10, "burst": 10, "sec": 86400},
            ],
            [
                rate_limter.per_week,
                {"limit": 10},
                {"limit": 10, "burst": 10, "sec": 604800},
            ],
            [
                rate_limter.per_sec,
                {"limit": 10, "burst": 5},
                {"limit": 10, "burst": 5, "sec": 1},
            ],
        ],
    )
    def test_per_xx(
        self,
        per_xx: Callable[[int, Optional[int]], Quota],
        constructor_kwargs: Dict[str, Any],
        expect: Dict[str, Any],
    ):
        quota: Quota = per_xx(**constructor_kwargs)
        assert quota.burst == expect["burst"]
        assert quota.get_limit() == expect["limit"]
        assert quota.get_period_sec() == expect["sec"]

    def test_per_duration(self):
        quota: Quota = rate_limter.per_duration(
            timedelta(minutes=2), limit=120, burst=150
        )
        assert quota.burst == 150
        assert quota.get_limit() == 120
        assert quota.get_period_sec() == 120
