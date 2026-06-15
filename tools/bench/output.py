"""Result metadata collection and JSON/markdown emitters"""
import platform
import subprocess  # noqa: S404
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603  # trusted args
        ['git', *args],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def collect_meta(repo_root: Path) -> dict[str, Any]:
    return {
        'commit': _git(repo_root, 'rev-parse', 'HEAD'),
        'branch': _git(repo_root, 'rev-parse', '--abbrev-ref', 'HEAD'),
        'dirty': _git(repo_root, 'status', '--porcelain') != '',
        'db_version': ROTKEHLCHEN_DB_VERSION,
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'ts': datetime.now(tz=UTC).isoformat(timespec='seconds'),
    }


def render_run_table(results: dict[str, dict[str, Any]]) -> str:
    """Markdown table for a single `run` result: profile/op → summary"""
    lines = [
        '| profile | operation | median ms | min ms | max ms | stddev |',
        '|---|---|---:|---:|---:|---:|',
    ]
    lines.extend(
        f'| {profile} | {op} | {s["median_ms"]} | {s["min_ms"]} | {s["max_ms"]} | {s["stddev_ms"]} |'  # noqa: E501
        for profile, ops in results.items()
        for op, s in ops.items()
    )
    return '\n'.join(lines)


def to_gha_benchmark(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert a `run` result to github-action-benchmark's
    customSmallerIsBetter format: one datapoint per profile/operation."""
    return [
        {
            'name': f'{profile}/{op}',
            'unit': 'ms',
            'value': summary['median_ms'],
            'extra': f'min {summary["min_ms"]}ms, stddev {summary["stddev_ms"]}ms',
        }
        for profile, ops in results.items()
        for op, summary in ops.items()
    ]


def render_compare_table(comparison: dict[str, dict[str, Any]]) -> str:
    """Markdown table for a `compare` result: per profile/op deltas"""
    lines = [
        '| profile | operation | base median | head median | Δ ms | Δ % | significant |',
        '|---|---|---:|---:|---:|---:|:---:|',
    ]
    for profile, ops in comparison.items():
        for op, c in ops.items():
            marker = '**yes**' if c['significant'] else 'no'
            sign = '+' if c['delta_ms'] >= 0 else ''
            lines.append(
                f'| {profile} | {op} | {c["base"]["median_ms"]} | {c["head"]["median_ms"]} '
                f'| {sign}{c["delta_ms"]} | {sign}{c["delta_pct"]}% | {marker} |',
            )
    return '\n'.join(lines)


def render_micro_compare_table(micro: dict[str, Any]) -> str:
    """Markdown section for the micro-benchmark A/B (`compare` result's 'micro' key).

    Falls back to a note when the base side could not run the head benchmarks.
    """
    if 'error' in micro:
        return (
            '### Micro-benchmark comparison\n\n'
            '_skipped: the base checkout could not run the head benchmark suite '
            '(a new benchmark may reference a head-only symbol)._'
        )
    if not (benchmarks := micro.get('benchmarks')):
        return ''

    lines = [
        '### Micro-benchmark comparison\n',
        '| benchmark | base median ms | head median ms | Δ ms | Δ % | significant |',
        '|---|---:|---:|---:|---:|:---:|',
    ]
    for name, c in benchmarks.items():
        marker = '**yes**' if c['significant'] else 'no'
        sign = '+' if c['delta_ms'] >= 0 else ''
        lines.append(
            f'| {name} | {c["base"]["median_ms"]} | {c["head"]["median_ms"]} '
            f'| {sign}{c["delta_ms"]} | {sign}{c["delta_pct"]}% | {marker} |',
        )
    return '\n'.join(lines)
