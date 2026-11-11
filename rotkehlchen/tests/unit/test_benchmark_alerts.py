import json
import runpy
import sys
from pathlib import Path
from typing import Final
from unittest.mock import patch

import pytest

from tools.bench.output import collect_machine, to_gha_benchmark

EPYC: Final = ('AMD EPYC 7763', 4)
XEON: Final = ('Intel Xeon 8370C', 4)


def _benches(machine: tuple[str, int] | None, min_ms: float, median_ms: float = 100) -> list:
    benches = to_gha_benchmark({'small': {'login': {
        'median_ms': median_ms, 'min_ms': min_ms, 'stddev_ms': 5,
    }}}, machine={} if machine is None else {
        'cpu_model': machine[0], 'logical_cpus': machine[1],
    })
    if machine is None:
        for bench in benches:
            bench['extra'] = bench['extra'].partition('\nmachine: ')[0]
    return benches


@pytest.mark.parametrize(('history', 'current', 'expected_previous'), [
    # slower fastest pass on the same runner CPU
    ([('aaa', EPYC, 90)], (EPYC, 120), 'aaa'),
    # a median inflated by a few slow passes, with a steady minimum, is noise
    ([('aaa', EPYC, 90)], (EPYC, 95, 300), None),
    # the latest datapoint ran on another CPU: compare against the older same-CPU one
    ([('aaa', EPYC, 90), ('bbb', XEON, 200)], (EPYC, 120), 'aaa'),
    ([('aaa', EPYC, 120), ('bbb', XEON, 60)], (EPYC, 120), None),
    # same CPU model with a different logical CPU count is other hardware
    ([('aaa', ('AMD EPYC 7763', 2), 50)], (EPYC, 120), None),
    # hardware never seen before, or unknown on either side
    ([('aaa', XEON, 50)], (EPYC, 120), None),
    ([('aaa', None, 50)], (EPYC, 120), None),
    ([('aaa', EPYC, 50)], (None, 120), None),
    ([], (EPYC, 120), None),
])
def test_benchmark_alerts(tmp_path, monkeypatch, history, current, expected_previous):
    """Alert on the fastest pass, against the latest datapoint on the same runner CPU"""
    (current_path := tmp_path / 'current.json').write_text(json.dumps(
        _benches(*current) + [{'name': 'new', 'value': 200}, {'name': 'invalid', 'value': None}],
    ))
    (history_path := tmp_path / 'data.js').write_text('window.BENCHMARK_DATA = ' + json.dumps({
        'entries': {'macro': [
            {'commit': {'id': commit}, 'benches': _benches(machine, min_ms)}
            for commit, machine, min_ms in history
        ]},
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
    expected = int(expected_previous is not None)
    assert github_output.read_text() == (
        f'has_alerts={str(expected > 0).lower()}\nalert_count={expected}\n'
    )
    if expected_previous is None:
        assert alert_path.read_text() == ''
    else:
        assert f'| `small/login` | `{current[1]}` ms | `90` ms | `{expected_previous}` |' in (
            alert_path.read_text()
        )


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
