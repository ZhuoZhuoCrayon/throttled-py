from typing import Any

import pytest
from throttled.store import BaseConnectionFactory, get_connection_factory


class TestRedisPool:
    def test_get_connection_factory(self):
        cls: BaseConnectionFactory = get_connection_factory()
        assert cls.__module__ == "throttled.store.redis_pool"
        assert cls.__class__.__name__ == "ConnectionFactory"

    @pytest.mark.parametrize(
        ("path", "options", "exc", "match"),
        [
            [
                None,
                {"CONNECTION_POOL_CLASS": "no-exists.redis.connection.ConnectionPool"},
                ImportError,
                # match is a regex pattern, so we need to escape the backslashes.
                'pip install "throttled-py\\[redis\\]"',
            ],
            [
                "no-exists.throttled.store.ConnectionFactory",
                None,
                ImportError,
                "No module named 'no-exists'",
            ],
            [
                "throttled.store.NotExistsConnectionFactory",
                None,
                ImportError,
                'does not define a "NotExistsConnectionFactory"',
            ],
            ["ABC", None, ImportError, "ABC doesn't look like a module path"],
        ],
        ids=[
            "ConnectionPool import error",
            "Module not found",
            "Class not found",
            "Invalid module path",
        ],
    )
    def test_get_connection_factory__raise(
        self,
        path: str | None,
        options: dict[str, Any] | None,
        exc: type[BaseException],
        match: str,
    ):
        with pytest.raises(exc, match=match):
            get_connection_factory(path, options)
