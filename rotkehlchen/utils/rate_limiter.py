import logging
import time
from collections.abc import Mapping
from types import TracebackType
from typing import Final, Self

import gevent
from gevent.lock import Semaphore

logger = logging.getLogger(__name__)

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

    Rates can be adjusted at runtime via widen() (when a probe or response
    headers reveal a higher tier), shrink_after_429() (when the upstream
    pushes back), and reset() (e.g. when the user changes their API key
    and we no longer trust the previously-discovered rate).
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

    def widen(self, observed_rps: float, observed_capacity: int | None = None) -> bool:
        """Raise rps and (optionally) capacity towards observed values.

        Never shrinks. Used when a probe or response headers reveal that the
        upstream allows more throughput than we are currently using. Returns
        True if anything actually changed.
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
            self.rps = max(_MIN_RPS_FLOOR, self.rps / 2)

    def reset(self, rps: float, capacity: int) -> None:
        """Hard-set rps and capacity (e.g. after an API key change)."""
        if rps <= 0 or capacity < 1:
            raise ValueError(f'invalid reset values: {rps=}, {capacity=}')
        with self._lock:
            self.rps = rps
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


# Header names this parser recognises, in priority order. We accept both
# RFC 9239 (RateLimit-*) and the de-facto X-RateLimit-* variant. Header
# lookup is case-insensitive via requests.structures.CaseInsensitiveDict, so
# we list canonical-case variants only.
_LIMIT_HEADERS: Final = ('RateLimit-Limit', 'X-RateLimit-Limit')
_REMAINING_HEADERS: Final = ('RateLimit-Remaining', 'X-RateLimit-Remaining')
_RESET_HEADERS: Final = ('RateLimit-Reset', 'X-RateLimit-Reset')


def _first_header(headers: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        if (value := headers.get(name)) is not None:
            return value
    return None


def parse_rate_limit_headers(
        headers: Mapping[str, str],
) -> tuple[float | None, int | None]:
    """Best-effort extraction of (rate-per-second, burst-capacity) from headers.

    Looks for RFC 9239 and X-RateLimit-* variants. The 'reset' field, when
    present, is interpreted as the window length in seconds — combined with
    'limit' to derive a rate per second (e.g. limit=300, reset=60 → 5 rps).

    Returns (None, None) when the headers don't provide enough information to
    infer a rate. The caller decides whether to widen the bucket.

    Returns:
        (rps, capacity) where rps may be None if no rate could be inferred
        and capacity may be None if no limit header was found.
    """
    limit_str = _first_header(headers, _LIMIT_HEADERS)
    reset_str = _first_header(headers, _RESET_HEADERS)
    if limit_str is None:
        return None, None

    try:
        limit = int(limit_str)
    except ValueError:
        logger.debug(f'rate_limiter: non-int Limit header value {limit_str!r}')
        return None, None

    if limit < 1:
        return None, None

    rps: float | None = None
    if reset_str is not None:
        try:
            reset_seconds = int(reset_str)
        except ValueError:
            reset_seconds = 0
        if reset_seconds > 0:
            rps = limit / reset_seconds

    # If we have a limit but no usable reset window, assume the limit applies
    # per second. That's the standard convention when only Limit is published.
    if rps is None:
        rps = float(limit)

    return rps, limit
