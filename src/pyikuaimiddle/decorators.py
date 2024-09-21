import functools
from typing import Any, Callable, Optional, Protocol
import threading
import time

__all__ = ["cache", "CacheWrapper", "Scheduler", "schedule", "only_one_running", "compress"]


class DecoratorType(Protocol):
    def __call__(self, func: Callable) -> Callable: ...


def compress(*decos: DecoratorType):
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
    def __init__(self, func, expire: float | int = 60) -> None:
        self._func = func
        self._expire = expire
        self._last_call: int | float = 0
        self._cache: Optional[Any] = None
        self._lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        with self._lock:
            if self._cache is None or time.time() - self._last_call >= self._expire:
                self._cache = self._func(*args, **kwargs)
                self._last_call = time.time()
        return self._cache


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
        return self._thread.start()

    def _schedule_worker(self):
        while True:
            time.sleep(self._interval)
            self._func()

    def __call__(self):
        return self._func()
