import json
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.bench.output import collect_machine, to_gha_benchmark


@pytest.mark.parametrize(
    ('previous_machine', 'current_machine', 'regressions', 'total', 'expected'), [
        (('AMD EPYC 7763', 4), ('AMD EPYC 9V74', 4), 3, 6, 0),
        (('AMD EPYC 7763', 4), ('AMD EPYC 7763', 2), 6, 6, 0),
        (('AMD EPYC 7763', 4), ('AMD EPYC 7763', 4), 6, 6, 6),
        (('AMD EPYC 7763', 4), ('AMD EPYC 9V74', 4), 1, 6, 1),
        (('AMD EPYC 7763', 4), ('AMD EPYC 9V74', 4), 2, 2, 2),
        (('AMD EPYC 7763', 4), ('AMD EPYC 9V74', 4), 3, 7, 3),
        (None, ('AMD EPYC 9V74', 4), 6, 6, 6),
        (('AMD EPYC 7763', 4), None, 6, 6, 6),
        (('', 4), ('AMD EPYC 9V74', 4), 6, 6, 6),
        (('AMD EPYC 7763', None), ('AMD EPYC 9V74', 4), 6, 6, 6),
    ],
)
def test_benchmark_runner_change_alerts(
        tmp_path, monkeypatch, previous_machine, current_machine, regressions, total, expected,
):
    """Suppress broad hardware shifts, but preserve isolated and unverified warnings."""
    current, previous = [], []
    for machine, benches, is_current in (
            (previous_machine, previous, False), (current_machine, current, True),
    ):
        benches.extend(to_gha_benchmark({'small': {
            f'operation-{index}': {
                'median_ms': 150 if is_current and index < regressions else 100,
                'min_ms': 90,
                'stddev_ms': 5,
            } for index in range(total)
        }}, machine={} if machine is None else {
            'cpu_model': machine[0], 'logical_cpus': machine[1],
        }))
        if machine is None:
            for bench in benches:
                bench['extra'] = bench['extra'].partition('\nmachine: ')[0]

    # New and invalid measurements must not dilute the comparable-test count.
    current.extend([{'name': 'new', 'value': 200}, {'name': 'invalid', 'value': None}])
    previous.extend([{'name': 'removed', 'value': 100}, {'name': 'invalid', 'value': 100}])
    (current_path := tmp_path / 'current.json').write_text(json.dumps(current))
    (history_path := tmp_path / 'data.js').write_text('window.BENCHMARK_DATA = ' + json.dumps({
        'entries': {'macro': [{'benches': previous}]},
    }))
    monkeypatch.setenv('GITHUB_OUTPUT', str(github_output := tmp_path / 'github-output'))
    monkeypatch.setattr(sys, 'argv', [
        'benchmark_alerts.py', '--current', str(current_path), '--data-js', str(history_path),
        '--bench-name', 'macro', '--threshold', '1.2', '--branch', 'develop', '--run-id', '123',
        '--output', str(alert_path := tmp_path / 'bench-alert.md'),
    ])
    runpy.run_path(
        str(Path(__file__).resolve().parents[3] / '.github/scripts/benchmark_alerts.py'),
        run_name='__main__',
    )
    assert github_output.read_text() == (
        f'has_alerts={str(expected > 0).lower()}\nalert_count={expected}\n'
    )
    if expected == 0:
        assert alert_path.read_text() == ''
    else:
        assert f'has {expected} benchmark(s)' in alert_path.read_text()


def test_benchmark_machine_metadata():
    with (
        patch('tools.bench.output.Path.read_text', return_value=(
            'processor\t: 0\nmodel name\t: AMD EPYC 7763\ncpu MHz\t: 2445.0\n'
        )),
        patch('tools.bench.output.os.cpu_count', return_value=4),
    ):
        assert (machine := collect_machine()) == {'cpu_model': 'AMD EPYC 7763', 'logical_cpus': 4}

    benches = to_gha_benchmark({'small': {'login': {
        'median_ms': 100, 'min_ms': 90, 'stddev_ms': 5,
    }}}, machine)
    assert benches == [{
        'name': 'small/login', 'unit': 'ms', 'value': 100,
        'extra': (
            'min 90ms, stddev 5ms\nmachine: {"cpu_model": "AMD EPYC 7763", "logical_cpus": 4}'
        ),
    }]
    with patch('tools.bench.output.Path.read_text', side_effect=FileNotFoundError):
        assert collect_machine() == {}
