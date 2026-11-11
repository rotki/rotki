#!/usr/bin/env python3

import argparse
import json
import logging
import operator
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
# The baseline is the median of this many latest same-hardware datapoints, so one
# night with a lucky fast pass does not make the next night alert.
BASELINE_DATAPOINTS: Final = 3

logger = logging.getLogger(__name__)

type Machine = tuple[str, int]  # CPU model, logical CPU count


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


def _machine(bench: dict[str, Any]) -> Machine | None:
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


# Per stored datapoint (newest first), its commit and each benchmark name mapped to
# the machine and the min it was measured with
type IndexedHistory = list[tuple[str | None, dict[str, tuple[Machine | None, float | None]]]]


def _index_history(history: list[dict[str, Any]]) -> IndexedHistory:
    """Parse every stored datapoint once, newest first."""
    return [(
        suite.get('commit', {}).get('id'),
        {
            bench['name']: (_machine(bench), _min_ms(bench))
            for bench in suite.get('benches', [])
            if isinstance(bench, dict) and isinstance(bench.get('name'), str)
        },
    ) for suite in reversed(history)]


def _same_machine_baseline(
        history: IndexedHistory,
        name: str,
        machine: Machine,
) -> tuple[float, str | None] | None:
    """Return the baseline min and its commit: the lower median of the latest
    BASELINE_DATAPOINTS datapoints of this benchmark measured on the same machine.
    Datapoints lacking the benchmark, a min or this machine are passed over."""
    datapoints: list[tuple[float, str | None]] = []
    for commit, benches in history:
        if (
                (entry := benches.get(name)) is not None and
                entry[0] == machine and
                entry[1] is not None
        ):
            datapoints.append((entry[1], commit))
            if len(datapoints) == BASELINE_DATAPOINTS:
                break

    if len(datapoints) == 0:
        return None
    # the lower median, so the baseline is always an actual stored datapoint
    return sorted(datapoints, key=operator.itemgetter(0))[(len(datapoints) - 1) // 2]


def _find_alerts(
        current: list[dict[str, Any]],
        history: list[dict[str, Any]],
        threshold: float,
) -> list[BenchmarkAlert]:
    """Compare the fastest pass of each benchmark against a baseline of the latest
    stored datapoints measured on the same runner CPU model and logical CPU count.
    Benchmarks with no machine or minimum recorded, or never measured on this hardware
    before, are skipped: across different runner CPUs the timings differ by more than
    the threshold."""
    alerts = []
    indexed_history = _index_history(history)
    for current_bench in current:
        if (
                not isinstance(name := current_bench.get('name'), str) or
                (current_machine := _machine(current_bench)) is None or
                (current_min := _min_ms(current_bench)) is None or
                (baseline := _same_machine_baseline(
                    history=indexed_history,
                    name=name,
                    machine=current_machine,
                )) is None
        ):
            continue

        previous_min, previous_commit = baseline
        if previous_min == 0:
            ratio = 1 if current_min == 0 else float('inf')
        else:
            ratio = current_min / previous_min

        if ratio > threshold:
            alerts.append(BenchmarkAlert(
                current=current_bench,
                current_min=current_min,
                previous_min=previous_min,
                previous_commit=previous_commit,
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
            f'the median of the latest {BASELINE_DATAPOINTS} datapoints on the same runner CPU '
            f'by more than `{threshold:.2f}x`.'
        ),
        f'Run: https://github.com/rotki/rotki/actions/runs/{run_id}',
        '',
        '| Benchmark | Current min | Baseline min | Baseline commit | Ratio |',
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
