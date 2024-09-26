import functools
from typing import Any, Callable
import threading
import time

__all__ = [
    "cache",
    "CacheWrapper",
    "Scheduler",
    "schedule",
    "only_one_running",
    "compress",
]


def compress(*decos: Callable[[Callable], Callable]):
    def deco(func: Callable):
        f = func
        for deco in reversed(decos):
            f = deco(f)
        return f

    return deco


def only_one_running(func):
    return functools.wraps(func)(OnlyOneRunning(func))


class OnlyOneRunning:
    def __init__(self, func) -> None:
        self._func = func
        self._lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        with self._lock:
            return self._func(*args, **kwargs)


def cache(expire: float | int = 60):
    def deco(func):
        return functools.wraps(func)(CacheWrapper(func, expire=expire))

    return deco


class CacheWrapper:
    def __init__(self, func, expire: float | int = 10) -> None:
        self._func = func
        self._expire = expire
        self._cache: dict = {}
        self._last_call: dict = {}
        self._lock = threading.Lock()

    def _cleanup(self):
        current_time = time.time()
        for key in list(self._cache.keys()):
            if current_time - self._last_call[key] >= self._expire:
                del self._cache[key]
                del self._last_call[key]

    def __call__(self, *args, **kwargs):
        if self._expire <= 0:
            return self._func(*args, **kwargs)

        key = (args, frozenset(kwargs.items()))
        with self._lock:
            self._cleanup()
            current_time = time.time()
            if (
                key not in self._cache
                or current_time - self._last_call.get(key, 0) >= self._expire
            ):
                self._cache[key] = self._func(*args, **kwargs)
                self._last_call[key] = current_time

        return self._cache[key]


def schedule(interval: float | int):
    def deco(func):
        return functools.wraps(func)(Scheduler(func, interval=interval))

    return deco


class Scheduler:
    def __init__(self, func: Callable[[], Any], interval: float | int) -> None:
        self._interval = interval
        self._func = func
        self._thread = threading.Thread(target=func, daemon=True)

    def start(self):
        if self._interval > 0:
            return self._thread.start()

    def _schedule_worker(self):
        while True:
            time.sleep(self._interval)
            self._func()

    def __call__(self):
        return self._func()
