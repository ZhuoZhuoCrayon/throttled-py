from typing import Callable, Union

from throttled.utils import now_mono_f

TimeLikeValue = Union[int, float]


class Timer:
    def __init__(self, clock: Callable[..., Union[int, float]] = None):
        self._clock: Callable[..., Union[int, float]] = clock or now_mono_f
        self._start: TimeLikeValue = 0

    def __enter__(self) -> "Timer":
        self._start: Union[int, float] = self._clock()
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def elapsed(self) -> TimeLikeValue:
        return self._clock() - self._start
