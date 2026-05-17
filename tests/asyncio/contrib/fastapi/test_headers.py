"""Unit tests for the shared rate-limit header renderer.

These tests target the renderer directly so the rendering contract
stays observable independently of the decorator and the middleware.
The custom-policy assertion fixes the design rule that header names
live only on the policy object.
"""

from __future__ import annotations

import math

from throttled.asyncio.contrib.fastapi.headers import (
    RateLimitContext,
    RateLimitHeaderPolicy,
    _inject_rate_limit_headers,  # noqa: PLC2701
)
from throttled.asyncio.rate_limiter import RateLimitResult


class TestInjectRateLimitHeadersDefaultPolicy:
    @classmethod
    def test_inject__success_path__omits_retry_after(cls) -> None:
        result = RateLimitResult(
            limited=False,
            state_values=(100, 99, 60.0, 0.0),
        )
        context = RateLimitContext(result=result, headers=RateLimitHeaderPolicy())
        headers: dict[str, str] = {}

        _inject_rate_limit_headers(headers, context, include_retry_after=False)

        assert headers == {
            "RateLimit-Limit": "100",
            "RateLimit-Remaining": "99",
            "RateLimit-Reset": str(math.ceil(60.0)),
        }

    @classmethod
    def test_inject__error_path__includes_retry_after(cls) -> None:
        result = RateLimitResult(
            limited=True,
            state_values=(100, 0, 60.0, 1.5),
        )
        context = RateLimitContext(result=result, headers=RateLimitHeaderPolicy())
        headers: dict[str, str] = {}

        _inject_rate_limit_headers(headers, context, include_retry_after=True)

        assert headers == {
            "RateLimit-Limit": "100",
            "RateLimit-Remaining": "0",
            "RateLimit-Reset": str(math.ceil(60.0)),
            "Retry-After": str(math.ceil(1.5)),
        }


class TestInjectRateLimitHeadersCustomPolicy:
    """Custom header names on the policy must replace the IETF
    defaults on both the success and the error paths. These tests
    fix the rule that header literals live only on the policy
    object, so the renderer and the call sites stay free of
    hardcoded names.
    """

    _CUSTOM_POLICY: RateLimitHeaderPolicy = RateLimitHeaderPolicy(
        limit="X-RateLimit-Limit",
        remaining="X-RateLimit-Remaining",
        reset="X-RateLimit-Reset",
        retry_after="X-Retry-After",
    )

    @classmethod
    def test_inject__custom_policy__error_path__uses_policy_names(cls) -> None:
        result = RateLimitResult(
            limited=True,
            state_values=(50, 0, 30.0, 2.0),
        )
        context = RateLimitContext(result=result, headers=cls._CUSTOM_POLICY)
        headers: dict[str, str] = {}

        _inject_rate_limit_headers(headers, context, include_retry_after=True)

        assert headers == {
            "X-RateLimit-Limit": "50",
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(math.ceil(30.0)),
            "X-Retry-After": str(math.ceil(2.0)),
        }

    @classmethod
    def test_inject__custom_policy__success_path__omits_retry_after(cls) -> None:
        result = RateLimitResult(
            limited=False,
            state_values=(50, 49, 30.0, 0.0),
        )
        context = RateLimitContext(result=result, headers=cls._CUSTOM_POLICY)
        headers: dict[str, str] = {}

        _inject_rate_limit_headers(headers, context, include_retry_after=False)

        assert headers == {
            "X-RateLimit-Limit": "50",
            "X-RateLimit-Remaining": "49",
            "X-RateLimit-Reset": str(math.ceil(30.0)),
        }
