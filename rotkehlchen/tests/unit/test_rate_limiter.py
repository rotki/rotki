import time

import gevent
import pytest

from rotkehlchen.utils.rate_limiter import TokenBucket


def test_burst_then_steady_rate() -> None:
    """A fresh bucket allows a burst up to capacity, then steadies at rps."""
    bucket = TokenBucket(rps=10, capacity=5)
    start = time.monotonic()
    for _ in range(5):  # burst should be instant
        bucket.acquire()
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.05, f'burst should be instant, took {burst_elapsed:.3f}s'

    bucket.acquire()  # 6th forces a wait of ~0.1s (1 token at 10rps)
    steady_elapsed = time.monotonic() - start
    assert 0.07 < steady_elapsed < 0.18, f'expected ~0.1s wait, got {steady_elapsed:.3f}s'


def test_concurrent_greenlets_share_rate() -> None:
    """Multiple greenlets sharing a bucket are gated together, not independently."""
    bucket = TokenBucket(rps=5, capacity=2)
    start = time.monotonic()
    greenlets = [gevent.spawn(bucket.acquire) for _ in range(7)]
    gevent.joinall(greenlets)
    elapsed = time.monotonic() - start
    # 7 requests through rps=5, burst=2: first 2 instant, remaining 5 cost ~1s total.
    assert 0.95 < elapsed < 1.25, f'expected ~1s, got {elapsed:.3f}s'


def test_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        TokenBucket(rps=0, capacity=1)
    with pytest.raises(ValueError):
        TokenBucket(rps=1, capacity=0)
