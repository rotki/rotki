import time
from types import TracebackType
from typing import Self

import gevent
from gevent.lock import Semaphore


class TokenBucket:
    """Gevent-friendly token-bucket rate limiter.

    A bucket of `capacity` tokens that refills at `rps` tokens per second.
    Each `acquire()` waits (via gevent.sleep) until at least one token is
    available, then consumes it.

    This gates the *rate* of operations across all greenlets that share the
    same instance — required when parallelizing calls against a shared
    upstream that has its own rate limit (e.g. etherscan-v2's single key
    across all EVM chains).
    """

    def __init__(self, rps: float, capacity: int) -> None:
        if rps <= 0:
            raise ValueError(f'rps must be positive, got {rps}')
        if capacity < 1:
            raise ValueError(f'capacity must be >= 1, got {capacity}')
        self.rps = rps
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = Semaphore()

    def _refill(self) -> None:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.rps)
        self.last_refill = now

    def acquire(self) -> None:
        """Block (via gevent.sleep) until a token is available, then consume one."""
        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait_s = (1 - self.tokens) / self.rps

            gevent.sleep(wait_s)

    def __enter__(self) -> Self:
        self.acquire()
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
    ) -> None:
        return None
