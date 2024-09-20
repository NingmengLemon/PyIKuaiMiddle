import threading
from typing import Literal


class ReadWriteLock:
    def __init__(self):
        self._readers = 0
        self._writer = False
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)

    def acquire_read(self):
        with self._lock:
            while self._writer:
                self._read_ready.wait()
            self._readers += 1

    def release_read(self):
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self):
        with self._lock:
            while self._writer or self._readers > 0:
                self._read_ready.wait()
            self._writer = True

    def release_write(self):
        with self._lock:
            self._writer = False
            self._read_ready.notify_all()

    def get_lock(self, rw: Literal["read", "write"]):
        if rw == "read":
            return self.read_lock()
        return self.write_lock()

    def read_lock(self):
        return _ReadLock(self)

    def write_lock(self):
        return _WriteLock(self)


class _ReadLock:
    def __init__(self, rw_lock: "ReadWriteLock"):
        self._rw_lock = rw_lock

    def __enter__(self):
        self._rw_lock.acquire_read()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._rw_lock.release_read()


class _WriteLock:
    def __init__(self, rw_lock: "ReadWriteLock"):
        self._rw_lock = rw_lock

    def __enter__(self):
        self._rw_lock.acquire_write()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._rw_lock.release_write()
