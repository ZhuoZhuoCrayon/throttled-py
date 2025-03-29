import asyncio
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from typing import Any, Callable, Coroutine, List


def now_sec() -> int:
    return int(time.time())


def now_ms() -> int:
    return int(time.time() * 1000)


class Benchmark:
    def __init__(self):
        self.handled_ns_list: List[int] = []
        self.start_times: List[int] = []
        self.end_times: List[int] = []
        self.last_avg: float = 0
        self.last_qps: float = 0

        self._loop = None
        self._has_checked_environment: bool = False

    def __enter__(self):
        self._checked_environment()
        self.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stats()

    async def __aenter__(self):
        self._checked_environment()
        self.clear()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.clear()

    def stats(self):
        total: int = len(self.handled_ns_list)
        avg: float = sum(self.handled_ns_list) / total
        qps: int = int(total / ((max(self.end_times) - min(self.start_times)) / 1e9))

        growth: str = "--"
        growth_rate: float = 0
        if self.last_qps:
            growth_rate: float = (qps - self.last_qps) * 100 / self.last_qps
            growth = f"{('⬆️', '⬇️')[growth_rate < 0]}{growth_rate:.2f}%"

        growth_emo: str = ("🚀", "💤")[growth_rate < 0]
        print(
            f"✅Total: {total}, "
            f"🕒Latency: {avg / 1e6:.4f} ms/op, "
            f"{growth_emo}Throughput: {qps} req/s ({growth})"
        )

        self.last_qps = qps
        self.last_avg = avg

    def clear(self):
        self.handled_ns_list.clear()
        self.end_times.clear()
        self.start_times.clear()

    def _checked_environment(self):
        if self._has_checked_environment:
            return

        self._has_checked_environment = True

        print(f"Python {sys.version}")
        print(f"Implementation: {platform.python_implementation()}")
        print(
            f"OS: {platform.system()} {platform.release()}, "
            f"Arch: {platform.machine()} \n"
        )

    def _timer(self, task: Callable[..., Any]) -> Callable[..., Any]:
        def inner(*args, **kwargs):
            start: int = time.perf_counter_ns()
            self.start_times.append(start)
            ret: Any = task(*args, **kwargs)
            end: int = time.perf_counter_ns()
            self.end_times.append(end)
            self.handled_ns_list.append(end - start)
            return ret

        return inner

    def concurrent(
        self, task: Callable[..., Any], batch: int, workers: int = 32, *args, **kwargs
    ) -> List[Any]:
        with self:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                return list(
                    executor.map(
                        lambda _: self._timer(task)(*args, **kwargs), range(batch)
                    )
                )

    def _atimer(self, task: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        async def inner(*args, **kwargs):
            start: int = time.perf_counter_ns()
            self.start_times.append(start)
            ret = await task(*args, **kwargs)
            end: int = time.perf_counter_ns()
            self.end_times.append(end)
            self.handled_ns_list.append(end - start)
            return ret

        return inner

    async def async_concurrent(
        self,
        task: Callable[..., Coroutine],
        batch: int,
        workers: int = 32,
        *args,
        **kwargs,
    ) -> List[Any]:
        if not self._loop:
            self._loop = asyncio.get_event_loop()

        sem = asyncio.Semaphore(workers)

        async def limited_task():
            async with sem:
                return await self._atimer(task)(*args, **kwargs)

        with self:
            return await asyncio.gather(*[limited_task() for __ in range(batch)])

    def serial(self, task: Callable[..., Any], batch: int, *args, **kwargs) -> List[Any]:
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


def import_string(dotted_path: str):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class'
            % (module_path, class_name)
        ) from err
