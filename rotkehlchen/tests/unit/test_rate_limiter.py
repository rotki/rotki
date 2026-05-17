import time

import gevent
import pytest

from rotkehlchen.utils.rate_limiter import TokenBucket


@pytest.fixture(autouse=True)
def _bypass_rate_limiter() -> None:
    """Override the conftest-level acquire() bypass.

    These tests exercise the real token-bucket pacing, so the global no-op
    monkeypatch in tests/conftest.py would defeat them. Returning None here
    runs no monkeypatch and leaves TokenBucket.acquire intact.
    """
    return


def test_burst_then_steady_rate() -> None:
    """A fresh bucket allows a burst up to capacity, then steadies at rps.

    Upper bounds are deliberately loose: the lower bounds prove pacing
    actually happened; the upper bounds only need to catch egregious bugs
    (infinite waits, off-by-orders-of-magnitude), not normal gevent
    scheduler drift on a loaded CI runner.
    """
    bucket = TokenBucket(rps=10, capacity=5)
    start = time.monotonic()
    for _ in range(5):  # burst should be near-instant (no gevent.sleep)
        bucket.acquire()
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.5, f'burst should be instant, took {burst_elapsed:.3f}s'

    bucket.acquire()  # 6th forces a wait of ~0.1s (1 token at 10rps)
    steady_elapsed = time.monotonic() - start
    assert 0.07 < steady_elapsed < 1.0, f'expected ~0.1s wait, got {steady_elapsed:.3f}s'


def test_concurrent_greenlets_share_rate() -> None:
    """Multiple greenlets sharing a bucket are gated together, not independently."""
    bucket = TokenBucket(rps=5, capacity=2)
    start = time.monotonic()
    greenlets = [gevent.spawn(bucket.acquire) for _ in range(7)]
    gevent.joinall(greenlets)
    elapsed = time.monotonic() - start
    # 7 requests through rps=5, burst=2: first 2 instant, remaining 5 cost ~1s
    # total. Upper bound is loose to absorb scheduler drift on loaded CI; the
    # lower bound is the meaningful check that pacing happened at all.
    assert 0.95 < elapsed < 3.0, f'expected ~1s, got {elapsed:.3f}s'


def test_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        TokenBucket(rps=0, capacity=1)
    with pytest.raises(ValueError):
        TokenBucket(rps=1, capacity=0)


def test_widen_only_grows() -> None:
    bucket = TokenBucket(rps=5, capacity=10)
    assert bucket.widen(observed_rps=20, observed_capacity=30) is True
    assert bucket.rps == 20
    assert bucket.capacity == 30

    # Same-or-lower observation must not shrink.
    assert bucket.widen(observed_rps=5, observed_capacity=5) is False
    assert bucket.rps == 20
    assert bucket.capacity == 30


def test_widen_respects_hysteresis() -> None:
    """Small observed deltas should not flap the bucket."""
    bucket = TokenBucket(rps=10, capacity=10)
    # 5% delta is below the 10% threshold — ignored.
    assert bucket.widen(observed_rps=10.5) is False
    assert bucket.rps == 10
    # 20% delta crosses the threshold — applied.
    assert bucket.widen(observed_rps=12) is True
    assert bucket.rps == 12


def test_shrink_after_429_has_floor() -> None:
    bucket = TokenBucket(rps=4, capacity=10)
    bucket.shrink_after_429()
    assert bucket.rps == 2
    bucket.shrink_after_429()
    assert bucket.rps == 1
    bucket.shrink_after_429()
    bucket.shrink_after_429()
    bucket.shrink_after_429()
    bucket.shrink_after_429()
    # Floor: never drops below 0.5.
    assert bucket.rps >= 0.5


def test_reset_can_shrink_or_grow() -> None:
    bucket = TokenBucket(rps=20, capacity=20)
    bucket.reset(rps=4, capacity=8)
    assert bucket.rps == 4
    assert bucket.capacity == 8
    # Outstanding tokens are clamped to the new capacity, never raised above it.
    assert bucket.tokens <= 8
