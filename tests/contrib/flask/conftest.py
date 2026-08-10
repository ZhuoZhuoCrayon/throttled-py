"""Fixtures for Flask contrib tests."""

from typing import TYPE_CHECKING, Any

import pytest
from flask import Flask
from throttled import RateLimiterType
from throttled.contrib.flask import Limiter
from throttled.store import MemoryStore

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def build_app() -> "Callable[..., tuple[Flask, Limiter]]":
    """Return a factory that produces a fresh ``(Flask, Limiter)`` pair
    per test. ``init_app`` is called automatically.
    """

    def _build(quota: str = "2/s", **limiter_kwargs: Any) -> tuple[Flask, Limiter]:
        limiter_kwargs.setdefault("store", MemoryStore())
        limiter: Limiter = Limiter(quota, **limiter_kwargs)
        app = Flask(__name__)
        limiter.init_app(app)
        return app, limiter

    return _build


ALGORITHMS: list[str] = [
    RateLimiterType.FIXED_WINDOW.value,
    RateLimiterType.SLIDING_WINDOW.value,
    RateLimiterType.TOKEN_BUCKET.value,
    RateLimiterType.LEAKING_BUCKET.value,
    RateLimiterType.GCRA.value,
]
