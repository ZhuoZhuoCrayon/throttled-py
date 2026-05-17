from __future__ import annotations

import string

import pytest
from throttled.asyncio.contrib.fastapi.keys import KeyParts, compose_key

_FIELD_SEPARATOR = "|"


class TestComposeKey:
    @classmethod
    def test_compose_key__basic__percent_encodes_reserved_chars(cls) -> None:
        expected: str = _FIELD_SEPARATOR.join(("GET", "%2Fitems", "10.0.0.1"))
        assert compose_key(KeyParts("GET", "/items", "10.0.0.1")) == expected

    @classmethod
    def test_compose_key__route_template__braces_are_encoded(cls) -> None:
        key: str = compose_key(KeyParts("GET", "/users/{user_id}", "alice"))
        assert "%7B" in key
        assert "%7D" in key
        assert "{" not in key
        assert "}" not in key

    @classmethod
    def test_compose_key__ipv6_principal__colons_are_encoded(cls) -> None:
        key: str = compose_key(KeyParts("GET", "/v", "2001:db8::42"))
        assert "2001%3Adb8%3A%3A42" in key
        assert ":" not in key

    @classmethod
    @pytest.mark.parametrize(
        ("a", "b"),
        [
            (
                KeyParts("GET", "/a:b", "c"),
                KeyParts("GET", "/a", "b:c"),
            ),
            (
                KeyParts("GET", "/users", "2001:db8::1"),
                KeyParts("GET", "/users:2001", "db8::1"),
            ),
            (
                KeyParts("GET", "/", "|pipe|"),
                KeyParts("GET", "/|pipe|", ""),
            ),
        ],
    )
    def test_compose_key__reserved_fields__no_collision(
        cls, a: KeyParts, b: KeyParts
    ) -> None:
        assert compose_key(a) != compose_key(b)

    @classmethod
    def test_compose_key__result__contains_only_safe_ascii(cls) -> None:
        key: str = compose_key(KeyParts("POST", "/x/{y}", "::1"))
        allowed: set[str] = set(
            string.ascii_letters + string.digits + "-._~%" + _FIELD_SEPARATOR
        )
        assert set(key).issubset(allowed), f"key contains unexpected characters: {key!r}"
