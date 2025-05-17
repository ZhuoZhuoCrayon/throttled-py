from typing import Any, Optional, Union

import pytest

from throttled.types import KeyT
from throttled.utils import format_key, to_bool


class TestUtils:
    @pytest.mark.parametrize(
        ["value", "expected"],
        [
            (None, None),
            ("", None),
            ("0", False),
            ("F", False),
            ("FALSE", False),
            ("N", False),
            ("NO", False),
            ("1", True),
            ("T", True),
            ("TRUE", True),
            ("Y", True),
            ("YES", True),
            (1, True),
            (0, False),
        ],
    )
    def test_to_bool(self, value: Any, expected: Optional[bool]):
        assert to_bool(value) == expected

    @pytest.mark.parametrize(
        ["key", "expect"],
        [
            (b"key", "key"),
            (b"key\x00", "key\x00"),
            ("key", "key"),
            ("key\x00", "key\x00"),
            (b"\x00", "\x00"),
            ("", ""),
        ],
    )
    def test_format_key(self, key: Union[bytes, str], expect: KeyT):
        assert format_key(key) == expect
