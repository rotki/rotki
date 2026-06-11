"""CLI for the macro benchmark harness.

    uv run python -m tools.bench run --profile small whale --samples 5
    uv run python -m tools.bench compare --base develop --profile small

`run` measures the current checkout and writes bench-result.json.
`compare` measures base and head interleaved on this machine and writes
bench-compare.json; its markdown table is the number a perf change cites.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from tools.bench.compare import run_compare
from tools.bench.harness import ensure_profile_cached, run_profile
from tools.bench.output import collect_meta, render_compare_table, render_run_table
from tools.bench.runner import BenchError
from tools.bench.stats import summarize

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_command(args: argparse.Namespace) -> None:
    work_dir = Path(tempfile.mkdtemp(prefix='rotki-bench-'))
    try:
        results = {}
        for profile in args.profile:
            cached = ensure_profile_cached(REPO_ROOT, profile)
            samples = run_profile(
                repo_root=REPO_ROOT,
                profile=profile,
                cached_profile=cached,
                blocks=args.samples,
                work_dir=work_dir,
            )
            results[profile] = {op: summarize(values) for op, values in samples.items()}
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    payload = {'meta': collect_meta(REPO_ROOT) | {'samples': args.samples}, 'results': results}
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'\nresults written to {args.output}\n')
    print(render_run_table(results))


def compare_command(args: argparse.Namespace) -> None:
    work_dir = Path(tempfile.mkdtemp(prefix='rotki-bench-'))
    try:
        result = run_compare(
            repo_root=REPO_ROOT,
            base_ref=args.base,
            profiles=args.profile,
            blocks=args.samples,
            work_dir=work_dir,
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    result['meta'] = collect_meta(REPO_ROOT)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'\nresults written to {args.output}\n')
    print(render_compare_table(result['profiles']))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='tools.bench',
        description='Macro benchmarks over golden user profiles',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Benchmark the current checkout')
    run_parser.add_argument('--profile', nargs='+', default=['small', 'whale'])
    run_parser.add_argument('--samples', type=int, default=5, help='Measurement blocks per profile')  # noqa: E501
    run_parser.add_argument('--output', type=Path, default=Path('bench-result.json'))
    run_parser.set_defaults(func=run_command)

    compare_parser = subparsers.add_parser('compare', help='A/B against a base ref')
    compare_parser.add_argument('--base', required=True, help='Base git ref (merge-base with HEAD is used)')  # noqa: E501
    compare_parser.add_argument('--profile', nargs='+', default=['small', 'whale'])
    compare_parser.add_argument('--samples', type=int, default=5, help='Interleaved block pairs per profile')  # noqa: E501
    compare_parser.add_argument('--output', type=Path, default=Path('bench-compare.json'))
    compare_parser.set_defaults(func=compare_command)

    args = parser.parse_args()
    try:
        args.func(args)
    except BenchError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
