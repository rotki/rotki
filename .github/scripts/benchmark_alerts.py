#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Keep the generated Markdown small enough to fit in a single Discord message.
MAX_ALERTS = 20
SCRIPT_PREFIX = 'window.BENCHMARK_DATA = '

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkAlert:
    current: dict[str, Any]
    previous: dict[str, Any]
    ratio: float


def _load_current(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding='utf8') as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f'{path} does not contain a benchmark list')

    return data


def _load_previous_suite(path: Path, bench_name: str) -> dict[str, Any] | None:
    if not path.exists():
        return None

    content = path.read_text(encoding='utf8').removeprefix(SCRIPT_PREFIX)

    data = json.loads(content)
    entries = data.get('entries', {})
    suites = entries.get(bench_name, [])
    if not suites:
        return None

    return suites[-1]


def _format_value(bench: dict[str, Any]) -> str:
    value = bench['value']
    unit = bench.get('unit', '')
    return f'`{value}` {unit}'.rstrip()


def _find_alerts(
        current: list[dict[str, Any]],
        previous_suite: dict[str, Any],
        threshold: float,
) -> list[BenchmarkAlert]:
    previous_by_name = {
        bench['name']: bench
        for bench in previous_suite.get('benches', [])
        if isinstance(bench, dict) and 'name' in bench
    }
    alerts = []
    for current_bench in current:
        if (previous_bench := previous_by_name.get(current_bench.get('name'))) is None:
            continue

        previous_value = previous_bench.get('value')
        current_value = current_bench.get('value')
        if (
                not isinstance(previous_value, int | float) or
                not isinstance(current_value, int | float)
        ):
            continue

        if previous_value == 0:
            ratio = 1 if current_value == 0 else float('inf')
        else:
            ratio = current_value / previous_value

        if ratio > threshold:
            alerts.append(BenchmarkAlert(
                current=current_bench,
                previous=previous_bench,
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
            f'`{bench_name}` has {len(alerts)} benchmark(s) worse than the previous nightly '
            f'datapoint by more than `{threshold:.2f}x`.'
        ),
        f'Run: https://github.com/rotki/rotki/actions/runs/{run_id}',
        '',
        '| Benchmark | Current | Previous | Ratio |',
        '|-|-|-|-|',
    ]
    lines.extend(
        f'| `{alert.current["name"]}` | {_format_value(alert.current)} | '
        f'{_format_value(alert.previous)} | `{alert.ratio:.2f}x` |'
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

    current = _load_current(args.current)
    previous_suite = _load_previous_suite(args.data_js, args.bench_name)
    if previous_suite is None:
        args.output.write_text('', encoding='utf8')
        _write_output('has_alerts', 'false')
        _write_output('alert_count', '0')
        return

    alerts = _find_alerts(current, previous_suite, args.threshold)
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
        logger.error(f'Failed to check benchmark alerts: {e}')
        sys.exit(1)
