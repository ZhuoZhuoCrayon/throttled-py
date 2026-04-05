from typing import cast

import pytest
from throttled import Quota, Throttled, per_sec, store
from throttled.exceptions import DataError
from throttled.rate_limiter import quota_parser

EXPECTED_MULTI_RULES = 2


def assert_quota(
    parsed_quota: Quota, *, limit: int, period_sec: int, burst: int | None = None
) -> None:
    assert parsed_quota.get_limit() == limit
    assert parsed_quota.get_period_sec() == period_sec
    assert parsed_quota.burst == (burst if burst is not None else limit)


class TestQuota:
    @classmethod
    @pytest.mark.parametrize(
        ("expression", "limit", "period_sec", "burst"),
        [
            ("100/s", 100, 1, 100),
            ("100 per second", 100, 1, 100),
            ("100 per seconds", 100, 1, 100),
            ("60/min", 60, 60, 60),
            ("60 per minute", 60, 60, 60),
            ("5 per hours", 5, 3600, 5),
            ("10/day", 10, 86400, 10),
            ("10/wk", 10, 604800, 10),
            ("7 / m ; burst=9", 7, 60, 9),
            ("1/s; burst=1", 1, 1, 1),
        ],
    )
    def test_parse__single_rule(
        cls, expression: str, limit: int, period_sec: int, burst: int
    ) -> None:
        parsed = quota_parser.parse(expression)
        assert isinstance(parsed, Quota)
        assert_quota(parsed, limit=limit, period_sec=period_sec, burst=burst)

    @classmethod
    def test_parse__multi_rules(cls) -> None:
        parsed = quota_parser.parse("1/s; burst=3 | 60/minute")
        assert isinstance(parsed, list)
        assert len(parsed) == EXPECTED_MULTI_RULES
        assert_quota(parsed[0], limit=1, period_sec=1, burst=3)
        assert_quota(parsed[1], limit=60, period_sec=60, burst=60)

    @classmethod
    def test_parse_many__always_return_list(cls) -> None:
        parsed = quota_parser.parse_many("10 per minute")
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert_quota(parsed[0], limit=10, period_sec=60)

    @classmethod
    @pytest.mark.parametrize(
        ("expression", "match"),
        [
            ("", "non-empty string"),
            ("   ", "non-empty string"),
            ("burst=1", "must follow a rate rule"),
            ("1/s; burst=1; burst=2", "duplicate burst"),
            ("0/s", "limit must be greater than 0"),
            ("10/month", "unsupported unit"),
            ("not-a-rule", "expected '<n>/<unit>' or '<n> per <unit>'"),
        ],
    )
    def test_parse__raise(cls, expression: str, match: str) -> None:
        with pytest.raises(DataError, match=match):
            quota_parser.parse(expression)


class TestThrottledQuota:
    @classmethod
    def test_constructor__string_quota_keep_backward_compatible(cls) -> None:
        mem_store: store.MemoryStore = store.MemoryStore()

        # New DSL path.
        throttle_with_str: Throttled = Throttled(
            key="quota-str",
            quota="1/s",
            store=mem_store,
        )
        assert not throttle_with_str.limit().limited

        # Existing Quota path stays compatible.
        throttle_with_quota: Throttled = Throttled(
            key="quota-object",
            quota=per_sec(1),
            store=mem_store,
        )
        assert not throttle_with_quota.limit().limited

    @classmethod
    def test_constructor__reject_multi_rules_string(cls) -> None:
        with pytest.raises(DataError, match="multiple quota rules"):
            Throttled(key="quota-multi", quota="1/s; 10/m", store=store.MemoryStore())

    @classmethod
    @pytest.mark.parametrize("bad_quota", [None, 123, 1.2, [], {}])
    def test_parse_many__reject_non_string(cls, bad_quota: object) -> None:
        with pytest.raises(DataError, match="non-empty string"):
            quota_parser.parse_many(cast(str, bad_quota))
