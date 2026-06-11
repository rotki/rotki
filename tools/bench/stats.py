"""Sample statistics and the A/B significance rule (design §4.2)"""
import statistics
from math import sqrt
from typing import Any


def summarize(samples: list[float]) -> dict[str, Any]:
    return {
        'samples_ms': [round(sample, 2) for sample in samples],
        'median_ms': round(statistics.median(samples), 2),
        'min_ms': round(min(samples), 2),
        'max_ms': round(max(samples), 2),
        'stddev_ms': round(statistics.stdev(samples), 2) if len(samples) > 1 else 0.0,
    }


def compare_samples(base: list[float], head: list[float]) -> dict[str, Any]:
    """Per-operation comparison: median delta plus a simple significance
    verdict — the delta must exceed 3x the pooled stddev of both sides.
    Deliberately conservative for small sample counts; scipy-based testing
    can replace this if sample counts are ever raised."""
    base_median, head_median = statistics.median(base), statistics.median(head)
    delta_ms = head_median - base_median
    pooled_stddev = sqrt(
        (statistics.stdev(base) ** 2 + statistics.stdev(head) ** 2) / 2,
    ) if min(len(base), len(head)) > 1 else 0.0
    return {
        'base': summarize(base),
        'head': summarize(head),
        'delta_ms': round(delta_ms, 2),
        'delta_pct': round(100 * delta_ms / base_median, 2) if base_median != 0 else 0.0,
        'significant': pooled_stddev > 0 and abs(delta_ms) > 3 * pooled_stddev,
    }
