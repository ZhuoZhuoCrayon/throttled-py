"""Quota DSL parser helpers."""

import re
from datetime import timedelta

from ..exceptions import DataError
from .base import Quota, per_duration

_UNIT_ALIAS_TO_CANONICAL: dict[str, str] = {
    "s": "second",
    "sec": "second",
    "secs": "second",
    "second": "second",
    "seconds": "second",
    "m": "minute",
    "min": "minute",
    "mins": "minute",
    "minute": "minute",
    "minutes": "minute",
    "h": "hour",
    "hr": "hour",
    "hrs": "hour",
    "hour": "hour",
    "hours": "hour",
    "d": "day",
    "day": "day",
    "days": "day",
    "w": "week",
    "wk": "week",
    "wks": "week",
    "week": "week",
    "weeks": "week",
}

_CANONICAL_UNIT_TO_DURATION: dict[str, timedelta] = {
    "second": timedelta(seconds=1),
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
}

_RATE_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<limit>\d+)
    \s*
    (?:
        /\s*(?P<slash_unit>[a-zA-Z]+)
        |
        per\s+(?P<per_unit>[a-zA-Z]+)
    )
    (?:\s+burst\s+(?P<burst>\d+))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_RULE_SPLITTER = re.compile(r"[;,|]")


def _parse_unit(raw_unit: str, token: str) -> str:
    canonical_unit: str | None = _UNIT_ALIAS_TO_CANONICAL.get(raw_unit.lower())
    if canonical_unit:
        return canonical_unit

    raise DataError(
        f"Invalid quota token: '{token}', unsupported unit '{raw_unit}'. "
        "Expected one of: s/sec/second, m/min/minute, h/hr/hour, d/day, w/wk/week."
    )


def _parse_rate_token(token: str) -> tuple[int, timedelta, int | None]:
    matched = _RATE_PATTERN.match(token)
    if not matched:
        raise DataError(
            f"Invalid quota token: '{token}', expected '<n>/<unit>' or "
            "'<n> per <unit>', optionally followed by 'burst <n>'."
        )

    limit: int = int(matched.group("limit"))
    if limit <= 0:
        raise DataError(f"Invalid quota token: '{token}', limit must be greater than 0.")

    raw_unit: str = matched.group("slash_unit") or matched.group("per_unit")
    canonical_unit = _parse_unit(raw_unit, token)
    burst_expr: str | None = matched.group("burst")
    burst: int | None = int(burst_expr) if burst_expr else None
    return limit, _CANONICAL_UNIT_TO_DURATION[canonical_unit], burst


def parse(quota_expr: str) -> list[Quota]:
    """Parse quota DSL string and return one or multiple quota rules.

    Supported forms:
    - ``n/unit`` (e.g. ``100/s``)
    - ``n per unit`` (e.g. ``100 per second``)
    - Optional ``burst <n>`` attached to the same rule
    - Multi-rule separators: ``,`` ``;`` ``|``
    """
    if not isinstance(quota_expr, str):
        raise DataError("Invalid quota: must be a non-empty string.")

    expression: str = quota_expr.strip()
    if not expression:
        raise DataError("Invalid quota: must be a non-empty string.")

    tokens: list[str] = [token.strip() for token in _RULE_SPLITTER.split(expression)]
    tokens = [token for token in tokens if token]
    if not tokens:
        raise DataError("Invalid quota: must be a non-empty string.")

    quotas: list[Quota] = []

    for token in tokens:
        limit, duration, burst = _parse_rate_token(token)
        quotas.append(
            per_duration(
                duration,
                limit,
                limit if burst is None else burst,
            )
        )
    return quotas
