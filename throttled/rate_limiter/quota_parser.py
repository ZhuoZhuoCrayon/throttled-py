"""Quota DSL parser helpers."""

import re
from datetime import timedelta

from ..exceptions import DataError
from .base import Quota, per_duration

ParsedQuotaT = Quota | list[Quota]

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
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_BURST_PATTERN = re.compile(r"^\s*burst\s*=\s*(?P<burst>\d+)\s*$", re.IGNORECASE)
_RULE_SPLITTER = re.compile(r"[;,|]")


def _parse_unit(raw_unit: str, token: str) -> str:
    canonical_unit: str | None = _UNIT_ALIAS_TO_CANONICAL.get(raw_unit.lower())
    if canonical_unit:
        return canonical_unit

    raise DataError(
        f"Invalid quota token: '{token}', unsupported unit '{raw_unit}'. "
        "Expected one of: s/sec/second, m/min/minute, h/hr/hour, d/day, w/wk/week."
    )


def _parse_rate_token(token: str) -> tuple[int, timedelta]:
    matched = _RATE_PATTERN.match(token)
    if not matched:
        raise DataError(
            f"Invalid quota token: '{token}', expected '<n>/<unit>' or '<n> per <unit>'."
        )

    limit: int = int(matched.group("limit"))
    if limit <= 0:
        raise DataError(f"Invalid quota token: '{token}', limit must be greater than 0.")

    raw_unit: str = matched.group("slash_unit") or matched.group("per_unit")
    canonical_unit = _parse_unit(raw_unit, token)
    return limit, _CANONICAL_UNIT_TO_DURATION[canonical_unit]


def parse_many(quota_expr: str) -> list[Quota]:
    """Parse quota DSL string and return one or multiple quota rules.

    Supported forms:
    - ``n/unit`` (e.g. ``100/s``)
    - ``n per unit`` (e.g. ``100 per second``)
    - Optional ``burst=<n>`` attached to the previous rule
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
    pending_limit: int | None = None
    pending_duration: timedelta | None = None
    pending_burst: int | None = None

    def finalize_pending_rule() -> None:
        nonlocal pending_limit
        nonlocal pending_duration
        nonlocal pending_burst

        if pending_limit is None or pending_duration is None:
            return

        quotas.append(
            per_duration(
                pending_duration,
                pending_limit,
                pending_limit if pending_burst is None else pending_burst,
            )
        )
        pending_limit = None
        pending_duration = None
        pending_burst = None

    for token in tokens:
        burst_match = _BURST_PATTERN.match(token)
        if burst_match:
            if pending_limit is None:
                raise DataError(
                    f"Invalid quota token: '{token}', "
                    "'burst=<n>' must follow a rate rule."
                )
            if pending_burst is not None:
                raise DataError(
                    f"Invalid quota token: '{token}', duplicate burst in the same rule."
                )
            pending_burst = int(burst_match.group("burst"))
            continue

        finalize_pending_rule()
        pending_limit, pending_duration = _parse_rate_token(token)

    finalize_pending_rule()
    return quotas


def parse(quota_expr: str) -> ParsedQuotaT:
    """Parse quota DSL string.

    Returns:
    - :class:`Quota` when the expression contains one rule.
    - ``list[Quota]`` when the expression contains multiple rules.
    """
    quotas = parse_many(quota_expr)
    return quotas[0] if len(quotas) == 1 else quotas
