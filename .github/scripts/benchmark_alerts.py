#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

# Keep the generated Markdown small enough to fit in a single Discord message.
MAX_ALERTS = 20
SCRIPT_PREFIX = 'window.BENCHMARK_DATA = '
# The fastest pass is what gets compared: the median of a few-millisecond operation
# swings with a couple of slow passes on a noisy runner, the minimum barely moves.
MIN_PATTERN: Final = re.compile(r'min ([0-9.]+)ms')

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkAlert:
    current: dict[str, Any]
    current_min: float
    previous_min: float
    previous_commit: str | None
    ratio: float


def _load_current(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding='utf8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f'{path} does not contain a benchmark list')

    return data


def _load_history(path: Path, bench_name: str) -> list[dict[str, Any]]:
    """Return the stored datapoints of the suite, oldest first"""
    if not path.exists():
        return []

    content = path.read_text(encoding='utf8').removeprefix(SCRIPT_PREFIX)
    return json.loads(content).get('entries', {}).get(bench_name, [])


def _min_ms(bench: dict[str, Any]) -> float | None:
    """Read the fastest pass persisted in github-action-benchmark's extra field."""
    if not isinstance(extra := bench.get('extra'), str):
        return None
    if (match := MIN_PATTERN.match(extra)) is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _machine(bench: dict[str, Any]) -> tuple[str, int] | None:
    """Read hardware persisted in github-action-benchmark's supported extra field."""
    if not isinstance(extra := bench.get('extra'), str):
        return None
    try:
        machine = json.loads(extra.partition('\nmachine: ')[2])
    except json.JSONDecodeError:
        return None

    if (
            isinstance(machine, dict) and
            isinstance(cpu_model := machine.get('cpu_model'), str) and cpu_model.strip() and
            isinstance(logical_cpus := machine.get('logical_cpus'), int) and logical_cpus > 0
    ):
        return cpu_model.strip(), logical_cpus
    return None


def _find_alerts(
        current: list[dict[str, Any]],
        history: list[dict[str, Any]],
        threshold: float,
) -> list[BenchmarkAlert]:
    """Compare the fastest pass of each benchmark against the latest stored datapoint
    measured on the same runner CPU model and logical CPU count. Benchmarks with no
    machine or minimum recorded, or never measured on this hardware before, are skipped:
    across different runner CPUs the timings differ by more than the threshold."""
    alerts = []
    for current_bench in current:
        if (
                (current_machine := _machine(current_bench)) is None or
                (current_min := _min_ms(current_bench)) is None
        ):
            continue

        for suite in reversed(history):
            previous_bench = next((
                bench for bench in suite.get('benches', [])
                if isinstance(bench, dict) and bench.get('name') == current_bench.get('name')
            ), None)
            if (
                    previous_bench is not None and
                    _machine(previous_bench) == current_machine and
                    (previous_min := _min_ms(previous_bench)) is not None
            ):
                break
        else:
            continue

        if previous_min == 0:
            ratio = 1 if current_min == 0 else float('inf')
        else:
            ratio = current_min / previous_min

        if ratio > threshold:
            alerts.append(BenchmarkAlert(
                current=current_bench,
                current_min=current_min,
                previous_min=previous_min,
                previous_commit=suite.get('commit', {}).get('id'),
                ratio=ratio,
            ))

    return sorted(alerts, key=lambda alert: alert.ratio, reverse=True)


def _write_output(name: str, value: str) -> None:
    if (github_output := os.environ.get('GITHUB_OUTPUT')) is not None:
        with Path(github_output).open('a', encoding='utf8') as f:
            f.write(f'{name}={value}\n')


def _render_alerts(
        alerts: list[BenchmarkAlert],
        branch: str,
        bench_name: str,
        threshold: float,
        run_id: str,
) -> str:
    if len(alerts) == 0:
        return ''

    lines = [
        f'## :warning: Benchmark regression alert ({branch})',
        '',
        (
            f'`{bench_name}` has {len(alerts)} benchmark(s) whose fastest pass is worse than '
            f'the latest datapoint on the same runner CPU by more than `{threshold:.2f}x`.'
        ),
        f'Run: https://github.com/rotki/rotki/actions/runs/{run_id}',
        '',
        '| Benchmark | Current min | Previous min | Previous commit | Ratio |',
        '|-|-|-|-|-|',
    ]
    lines.extend(
        f'| `{alert.current["name"]}` | `{alert.current_min:g}` ms | '
        f'`{alert.previous_min:g}` ms | '
        f'{"`" + alert.previous_commit[:10] + "`" if alert.previous_commit else "?"} | '
        f'`{alert.ratio:.2f}x` |'
        for alert in alerts[:MAX_ALERTS]
    )

    if len(alerts) > MAX_ALERTS:
        lines.append(
            f'\n...and {len(alerts) - MAX_ALERTS} more benchmark(s). '
            'See the workflow artifact for the full benchmark output.',
        )

    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description='Find nightly benchmark regressions')
    parser.add_argument('--current', required=True, type=Path)
    parser.add_argument('--data-js', required=True, type=Path)
    parser.add_argument('--bench-name', required=True)
    parser.add_argument('--threshold', required=True, type=float)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    alerts = _find_alerts(
        current=_load_current(args.current),
        history=_load_history(args.data_js, args.bench_name),
        threshold=args.threshold,
    )
    args.output.write_text(
        _render_alerts(alerts, args.branch, args.bench_name, args.threshold, args.run_id),
        encoding='utf8',
    )
    _write_output('has_alerts', str(len(alerts) > 0).lower())
    _write_output('alert_count', str(len(alerts)))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as e:
        logger.error('Failed to check benchmark alerts: %s', e)
        sys.exit(1)
