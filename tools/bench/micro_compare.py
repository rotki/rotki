"""Micro-benchmark A/B: run the pytest-benchmark suite on base and head.

The macro comparison can only exercise code reachable through the API with no
network egress. Some optimizations live on paths that need the network and so
are invisible to it -- e.g. the per-transaction redecode deletion
(`delete_events_by_tx_ref`), which only the `test_redecode_delete_customized_lookup`
micro-benchmark measures. This module runs the whole micro suite against both
sides and compares, so such wins (and regressions) surface on the PR too.

HEAD's benchmark files are used in both checkouts: the same measurement code
runs against each side's backend, mirroring how the macro side shares HEAD's
profile and operations. pytest-benchmark does its own repeated rounds, so a
single suite run per side already yields a stable median/stddev.
"""
import json
import shutil
import subprocess  # noqa: S404
from math import sqrt
from pathlib import Path
from typing import Any

from tools.bench.runner import BenchError

BENCH_DIR = Path('rotkehlchen') / 'tests' / 'benchmarks'


def _run_micro_suite(side_root: Path, json_out: Path) -> dict[str, dict[str, float]]:
    """Run the pytest-benchmark suite in side_root and return per-benchmark stats in ms.

    Raises BenchError if the suite produced no json (import/collection failure), so the
    caller can degrade gracefully instead of comparing against missing data.
    """
    result = subprocess.run(  # noqa: S603  # trusted args
        [  # noqa: S607
            'uv', 'run', 'python', 'pytestgeventwrapper.py',
            '-m', 'benchmark', '--benchmark-only', '--benchmark-columns=median,min,stddev',
            f'--benchmark-json={json_out}', str(BENCH_DIR),
        ],
        cwd=side_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if not json_out.exists() or json_out.stat().st_size == 0:
        raise BenchError(
            f'micro suite produced no json in {side_root}:\n'
            f'{result.stdout[-2000:]}\n{result.stderr[-2000:]}',
        )

    try:
        data = json.loads(json_out.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise BenchError(
            f'micro suite json unreadable in {side_root}: {e}\n'
            f'{result.stdout[-2000:]}\n{result.stderr[-2000:]}',
        ) from e
    return {
        benchmark['name']: {
            'median_ms': round(benchmark['stats']['median'] * 1000, 3),
            'min_ms': round(benchmark['stats']['min'] * 1000, 3),
            'stddev_ms': round(benchmark['stats']['stddev'] * 1000, 3),
        }
        for benchmark in data['benchmarks']
    }


def _compare_stats(base: dict[str, float], head: dict[str, float]) -> dict[str, Any]:
    """Compare one benchmark's base/head stats. Same significance rule as the macro
    side: the median delta must exceed 3x the pooled stddev of both runs."""
    delta_ms = head['median_ms'] - base['median_ms']
    pooled_stddev = sqrt((base['stddev_ms'] ** 2 + head['stddev_ms'] ** 2) / 2)
    return {
        'base': base,
        'head': head,
        'delta_ms': round(delta_ms, 3),
        'delta_pct': round(100 * delta_ms / base['median_ms'], 2) if base['median_ms'] else 0.0,
        'significant': pooled_stddev > 0 and abs(delta_ms) > 3 * pooled_stddev,
    }


def run_micro_compare(repo_root: Path, worktree: Path, work_dir: Path) -> dict[str, Any]:
    """Run the micro suite on base (worktree) and head (repo_root) and compare.

    Returns {'benchmarks': {name: comparison}} or {'error': reason} when the base side
    cannot run the head benchmarks (e.g. a new benchmark references a head-only symbol),
    so a benchmark-only change never fails the whole bench job.
    """
    head_bench, base_bench = repo_root / BENCH_DIR, worktree / BENCH_DIR
    shutil.rmtree(base_bench, ignore_errors=True)
    shutil.copytree(head_bench, base_bench, ignore=shutil.ignore_patterns('__pycache__'))

    micro_dir = work_dir / 'micro'
    micro_dir.mkdir(parents=True, exist_ok=True)
    try:
        base_stats = _run_micro_suite(worktree, micro_dir / 'base.json')
        head_stats = _run_micro_suite(repo_root, micro_dir / 'head.json')
    except BenchError as e:
        return {'error': str(e)}

    return {'benchmarks': {
        name: _compare_stats(base=base_stats[name], head=head_stats[name])
        for name in base_stats
        if name in head_stats
    }}
