from typing import Any, Optional

import pytest

from throttled.utils import to_bool


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
