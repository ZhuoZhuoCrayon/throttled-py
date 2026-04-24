import asyncio
import platform
import sys
import time
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from importlib import import_module
from types import TracebackType

from . import types


def format_value(value: types.StoreValueT) -> types.StoreValueT:
    """Normalize a numeric-like value to ``int`` or ``float``."""
    float_value: float = float(value)
    if float_value.is_integer():
        return int(float_value)
    return float_value


def format_key(key: bytes | str) -> types.KeyT:
    """Normalize a key value to the internal key type."""
    if isinstance(key, bytes):
        return key.decode("utf-8")
    return key


def format_kv(
    kv: dict[types.KeyT, types.StoreValueT],
) -> types.StoreDictValueT:
    """Normalize key-value mapping types returned from stores."""
    return {format_key(k): format_value(v) for k, v in kv.items()}


def now_sec() -> int:
    """Return current wall-clock time in seconds."""
    return int(time.time())


def now_mono_f() -> float:
    """Return current monotonic clock time in seconds."""
    return time.monotonic()


def now_ms() -> int:
    """Return current wall-clock time in milliseconds."""
    return int(time.time() * 1000)


FALSE_STRINGS: tuple[str, ...] = ("0", "F", "FALSE", "N", "NO")


def to_bool(value: object | None) -> bool | None:
    """Convert a value into ``bool`` while preserving empty semantics."""
    if value is None or (isinstance(value, str) and not value):
        return None
    if isinstance(value, str) and value.upper() in FALSE_STRINGS:
        return False
    return bool(value)


class Timer:
    """Measure elapsed time for sync and async call scopes."""

    def __init__(
        self,
        clock: Callable[[], types.TimeLikeValueT] | None = None,
        callback: Callable[
            [types.TimeLikeValueT, types.TimeLikeValueT, types.TimeLikeValueT], object
        ]
        | None = None,
    ) -> None:
        self._clock: Callable[[], types.TimeLikeValueT] = clock or now_mono_f
        self._callback: (
            Callable[
                [types.TimeLikeValueT, types.TimeLikeValueT, types.TimeLikeValueT],
                object,
            ]
            | None
        ) = callback
        self._start: types.TimeLikeValueT = 0

    def _new_timer(self) -> "Timer":
        return self.__class__(self._clock, self._callback)

    def __enter__(self) -> "Timer":
        self._start = self._clock()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._handle_callback()

    async def __aenter__(self) -> "Timer":
        self._start = self._clock()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._handle_callback()

    def _handle_callback(self) -> None:
        if self._callback is not None:
            end: types.TimeLikeValueT = self._clock()
            elapsed: types.TimeLikeValueT = end - self._start
            self._callback(elapsed, self._start, end)

    def __call__(self, func: Callable[types.P, types.R]) -> Callable[types.P, types.R]:
        @wraps(func)
        def _inner(*args: types.P.args, **kwargs: types.P.kwargs) -> types.R:
            with self._new_timer():
                return func(*args, **kwargs)

        return _inner


class Benchmark:
    """Simple benchmark helper for sync and async callable execution."""

    def __init__(self) -> None:
        self.handled_ns_list: list[int] = []
        self.start_times: list[int] = []
        self.end_times: list[int] = []
        self.last_avg: float = 0
        self.last_qps: float = 0

        self._loop: asyncio.AbstractEventLoop | None = None
        self._has_checked_environment: bool = False

    def __enter__(self) -> "Benchmark":
        self._checked_environment()
        self.clear()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stats()

    async def __aenter__(self) -> "Benchmark":
        self._checked_environment()
        self.clear()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stats()

    def stats(self) -> None:
        total: int = len(self.handled_ns_list)
        if total == 0:
            return
        avg: float = sum(self.handled_ns_list) / total
        qps: int = int(total / ((max(self.end_times) - min(self.start_times)) / 1e9))

        growth: str = "--"
        growth_rate: float = 0
        if self.last_qps:
            growth_rate = (qps - self.last_qps) * 100 / self.last_qps
            growth = f"{('⬆️', '⬇️')[growth_rate < 0]}{growth_rate:.2f}%"

        growth_emo: str = ("🚀", "💤")[growth_rate < 0]
        print(
            f"✅ Total: {total}, "
            f"🕒 Latency: {avg / 1e6:.4f} ms/op, "
            f"{growth_emo} Throughput: {qps} req/s ({growth})"
        )

        self.last_qps = qps
        self.last_avg = avg

    def clear(self) -> None:
        self.handled_ns_list.clear()
        self.end_times.clear()
        self.start_times.clear()

    def _checked_environment(self) -> None:
        if self._has_checked_environment:
            return

        self._has_checked_environment = True
        print(f"Python {sys.version}")
        print(f"Implementation: {platform.python_implementation()}")
        print(
            f"OS: {platform.system()} {platform.release()}, "
            f"Arch: {platform.machine()} \n"
        )

    def _timer(self, task: Callable[types.P, types.R]) -> Callable[types.P, types.R]:
        @wraps(task)
        def inner(*args: types.P.args, **kwargs: types.P.kwargs) -> types.R:
            start: int = time.perf_counter_ns()
            self.start_times.append(start)
            ret: types.R = task(*args, **kwargs)
            end: int = time.perf_counter_ns()
            self.end_times.append(end)
            self.handled_ns_list.append(end - start)
            return ret

        return inner

    def concurrent(
        self,
        task: Callable[types.P, types.R],
        batch: int,
        workers: int = 32,
        *args: types.P.args,
        **kwargs: types.P.kwargs,
    ) -> list[types.R]:
        with self, ThreadPoolExecutor(max_workers=workers) as executor:
            return list(
                executor.map(lambda _: self._timer(task)(*args, **kwargs), range(batch))
            )

    def _atimer(
        self,
        task: Callable[types.P, Coroutine[object, object, types.R]],
    ) -> Callable[types.P, Coroutine[object, object, types.R]]:
        @wraps(task)
        async def inner(*args: types.P.args, **kwargs: types.P.kwargs) -> types.R:
            start: int = time.perf_counter_ns()
            self.start_times.append(start)
            ret: types.R = await task(*args, **kwargs)
            end: int = time.perf_counter_ns()
            self.end_times.append(end)
            self.handled_ns_list.append(end - start)
            return ret

        return inner

    async def async_concurrent(
        self,
        task: Callable[types.P, Coroutine[object, object, types.R]],
        batch: int,
        workers: int = 32,
        *args: types.P.args,
        **kwargs: types.P.kwargs,
    ) -> list[types.R]:
        if not self._loop:
            self._loop = asyncio.get_event_loop()

        sem = asyncio.Semaphore(workers)

        async def limited_task() -> types.R:
            async with sem:
                return await self._atimer(task)(*args, **kwargs)

        async with self:
            return await asyncio.gather(*[limited_task() for __ in range(batch)])

    async def async_serial(
        self,
        task: Callable[types.P, Coroutine[object, object, types.R]],
        batch: int,
        *args: types.P.args,
        **kwargs: types.P.kwargs,
    ) -> list[types.R]:
        async with self:
            return [await self._atimer(task)(*args, **kwargs) for __ in range(batch)]

    def serial(
        self,
        task: Callable[types.P, types.R],
        batch: int,
        *args: types.P.args,
        **kwargs: types.P.kwargs,
    ) -> list[types.R]:
        with self:
            return [self._timer(task)(*args, **kwargs) for __ in range(batch)]


# --------------------------------------------------------------------------------------
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


def import_string(dotted_path: str) -> object:
    """Import a dotted module path and return the designated attribute or class.

    The last name in the path is treated as the attribute/class name.
    Raise ImportError if the import fails.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError(f"{dotted_path} doesn't look like a module path") from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            f'Module "{module_path}" does not define a "{class_name}" attribute/class'
        ) from err
