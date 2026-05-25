import time
from types import TracebackType
from typing import Final, Self

import gevent
from gevent.lock import Semaphore

# Hysteresis: don't churn the bucket on every response. Only update when the
# observed rate differs from the current by at least this fraction.
_UPDATE_THRESHOLD: Final = 0.10
# Floor that shrink_after_429 won't drop below. Stops a misbehaving upstream
# from pinning us at zero throughput.
_MIN_RPS_FLOOR: Final = 0.5


class TokenBucket:
    """Gevent-friendly token-bucket rate limiter.

    Think of it as a bucket holding `capacity` tokens. Each `acquire()` call
    consumes one token; if the bucket is empty, the caller waits (via
    gevent.sleep) until a token is available. The bucket refills
    continuously at `rps` (requests per second) tokens per second, up to
    `capacity`.

    The two parameters control different things:
    - `rps`: the steady-state rate — how many calls per second are allowed
      on average over time. This is the long-term throughput ceiling. For
      example, `rps=5` means after the bucket is drained, callers proceed
      at roughly one per 200ms.
    - `capacity`: the burst allowance — how many calls can fire back-to-back
      after a quiet period before pacing kicks in. A larger capacity lets
      short bursts (e.g. fanning out a parallel call across many chains)
      go through instantly; a smaller one spreads the same calls evenly.

    This gates operations across all greenlets that share the same instance
    — required when parallelizing calls against a shared upstream that has
    its own rate limit (e.g. etherscan-v2's single key across all EVM
    chains).

    Rates can be adjusted at runtime via widen() (when a probe reveals a
    higher tier), shrink_after_429() (when the upstream pushes back), and
    reset() (e.g. when the user changes their API key and we no longer
    trust the previously-discovered rate).
    """

    def __init__(self, rps: float, capacity: int, minimum_rps: float = _MIN_RPS_FLOOR) -> None:
        if rps <= 0:
            raise ValueError(f'rps must be positive, got {rps}')
        if capacity < 1:
            raise ValueError(f'capacity must be >= 1, got {capacity}')
        if minimum_rps <= 0:
            raise ValueError(f'minimum_rps must be positive, got {minimum_rps}')
        self.rps = rps
        self.minimum_rps = minimum_rps
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

    def widen(self, observed_rps: float, observed_capacity: int | None = None) -> bool:
        """Raise rps and (optionally) capacity towards observed values.

        Never shrinks. Used when a probe reveals that the upstream allows
        more throughput than we are currently using. Returns True if
        anything actually changed.
        """
        if observed_rps <= 0:
            return False

        with self._lock:
            changed = False
            if observed_rps > self.rps * (1 + _UPDATE_THRESHOLD):
                self.rps = observed_rps
                changed = True
            if observed_capacity is not None and observed_capacity > self.capacity:
                self.capacity = float(observed_capacity)
                changed = True
            return changed

    def shrink_after_429(self) -> None:
        """Halve rps (with a floor) after a 429. Capacity untouched."""
        with self._lock:
            self.rps = max(self.minimum_rps, self.rps / 2)

    def reset(self, rps: float, capacity: int, minimum_rps: float | None = None) -> None:
        """Hard-set rps and capacity (e.g. after an API key change)."""
        if rps <= 0 or capacity < 1:
            raise ValueError(f'invalid reset values: {rps=}, {capacity=}')
        if minimum_rps is not None and minimum_rps <= 0:
            raise ValueError(f'invalid reset value: {minimum_rps=}')
        with self._lock:
            self.rps = rps
            if minimum_rps is not None:
                self.minimum_rps = minimum_rps
            self.capacity = float(capacity)
            self.tokens = min(self.tokens, self.capacity)

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
