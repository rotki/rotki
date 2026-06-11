"""CLI for building golden user profiles.

    uv run python -m tools.scenarios build --profile whale --output /tmp/whale-data
    uv run python -m tools.scenarios list

Builds are cached under ~/.cache/rotki-scenarios keyed by (profile, DB schema
version, generator+globaldb hash). The cached copy must stay pristine: always
materialize to an --output directory before booting a backend on it.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import TRACE, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from tools.scenarios.base import USER_PASSWORD, ProfileBuilder
from tools.scenarios.cache import (
    cached_profile_path,
    commit_build,
    compute_cache_key,
    materialize,
    new_build_dir,
)
from tools.scenarios.profiles.registry import PROFILES


def build_command(args: argparse.Namespace) -> None:
    key = compute_cache_key(args.profile)
    cached = None if args.force else cached_profile_path(key)
    build_seconds = None
    if cached is None:
        add_logging_level('TRACE', TRACE)
        configure_logging(default_args())
        build_dir = new_build_dir(key)
        start = time.perf_counter()
        builder = ProfileBuilder(name=args.profile, output_dir=build_dir)
        extra = PROFILES[args.profile](builder)
        expected = builder.finalize(extra)
        GlobalDBHandler().conn.close()  # checkpoint the WAL before caching
        build_seconds = round(time.perf_counter() - start, 2)
        cached = commit_build(key, build_dir)
    else:
        expected = json.loads(
            (cached / 'users' / args.profile / 'expected.json').read_text(encoding='utf-8'),
        )

    if args.output is not None:
        materialize(cached, args.output)

    print(json.dumps({
        'profile': args.profile,
        'cache_key': key,
        'cache_path': str(cached),
        'cache_hit': build_seconds is None,
        'build_seconds': build_seconds,
        'output': str(args.output) if args.output is not None else None,
        'username': args.profile,
        'password': USER_PASSWORD,
        'expected': expected,
    }, indent=2))


def list_command(_args: argparse.Namespace) -> None:
    for name, build_fn in sorted(PROFILES.items()):
        doc = (sys.modules[build_fn.__module__].__doc__ or '').strip().splitlines()[0]
        print(f'{name}: {doc}')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='tools.scenarios',
        description='Build deterministic golden user profiles for measurement',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)
    build_parser = subparsers.add_parser('build', help='Build (or fetch cached) a profile')
    build_parser.add_argument('--profile', required=True, choices=sorted(PROFILES))
    build_parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Materialize the built profile into this (non-existing) data directory',
    )
    build_parser.add_argument(
        '--force',
        action='store_true',
        help='Rebuild even on a cache hit',
    )
    build_parser.set_defaults(func=build_command)
    list_parser = subparsers.add_parser('list', help='List available profiles')
    list_parser.set_defaults(func=list_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
