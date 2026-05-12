import time

import gevent
import pytest

from rotkehlchen.utils.rate_limiter import TokenBucket, parse_rate_limit_headers


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


def test_parse_rfc9239_headers() -> None:
    rps, cap = parse_rate_limit_headers({
        'RateLimit-Limit': '300',
        'RateLimit-Reset': '60',
    })
    assert rps == 5  # 300 per 60s window
    assert cap == 300


def test_parse_x_ratelimit_headers() -> None:
    rps, cap = parse_rate_limit_headers({
        'X-RateLimit-Limit': '100',
        'X-RateLimit-Reset': '1',
    })
    assert rps == 100
    assert cap == 100


def test_parse_limit_only_assumes_per_second() -> None:
    rps, cap = parse_rate_limit_headers({'X-RateLimit-Limit': '30'})
    assert rps == 30
    assert cap == 30


def test_parse_missing_or_malformed_headers() -> None:
    assert parse_rate_limit_headers({}) == (None, None)
    assert parse_rate_limit_headers({'X-RateLimit-Limit': 'unlimited'}) == (None, None)
    assert parse_rate_limit_headers({'X-RateLimit-Limit': '0'}) == (None, None)
