from collections.abc import Iterator
from contextlib import contextmanager

import gevent.lock


class HistoryProcessingCoordinator:
    def __init__(self) -> None:
        self._lock = gevent.lock.Semaphore()
        self._active_history_fetches = 0

    @contextmanager
    def history_fetch(self) -> Iterator[None]:
        with self._lock:
            self._active_history_fetches += 1
        try:
            yield
        finally:
            with self._lock:
                self._active_history_fetches -= 1

    def is_history_fetching(self) -> bool:
        with self._lock:
            return self._active_history_fetches > 0
