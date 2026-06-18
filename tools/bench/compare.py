"""A/B comparison: base and head interleaved on the same machine (design §4.2).

The base ref is checked out into a temporary git worktree with its own venv;
profiles are built once by the HEAD generator and shared by both sides.
Blocks alternate base/head (ABAB…) so thermal and load drift hits both sides
equally.
"""
import os
import re
import shutil
import subprocess  # noqa: S404
import tempfile
from pathlib import Path
from typing import Any

from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from tools.bench.harness import ensure_profile_cached, load_expected, run_block
from tools.bench.micro_compare import run_micro_compare
from tools.bench.runner import BenchError
from tools.bench.stats import compare_samples


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603  # trusted args
        ['git', *args],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BenchError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def _worktree_db_version(worktree: Path) -> int:
    content = (worktree / 'rotkehlchen' / 'db' / 'settings.py').read_text(encoding='utf-8')
    if (match := re.search(r'^ROTKEHLCHEN_DB_VERSION\s*(?::\s*\w+\s*)?=\s*(\d+)', content, re.MULTILINE)) is None:  # noqa: E501
        raise BenchError('could not parse ROTKEHLCHEN_DB_VERSION from the base worktree')
    return int(match.group(1))


def _setup_worktree(repo_root: Path, base_commit: str) -> Path:
    worktree = Path(tempfile.mkdtemp(prefix='rotki-bench-base-'))
    worktree.rmdir()  # git worktree add wants to create it
    _git(repo_root, 'worktree', 'add', '--detach', str(worktree), base_commit)

    if (base_version := _worktree_db_version(worktree)) != ROTKEHLCHEN_DB_VERSION:
        _teardown_worktree(repo_root, worktree)
        raise BenchError(
            f'base DB schema version ({base_version}) differs from head '
            f'({ROTKEHLCHEN_DB_VERSION}). Per-side profile builds are not supported '
            f'yet — pick a base ref at the same schema version.',
        )

    env = {k: v for k, v in os.environ.items() if k != 'VIRTUAL_ENV'}
    sync = subprocess.run(
        # --all-groups so the worktree gets the full test infra the micro suite needs
        # (pytest-benchmark, and pylint which the test conftest imports eagerly)
        ['uv', 'sync', '--all-groups'],  # noqa: S607
        cwd=worktree,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if sync.returncode != 0:
        _teardown_worktree(repo_root, worktree)
        raise BenchError(f'uv sync in base worktree failed:\n{sync.stderr}')
    return worktree


def _teardown_worktree(repo_root: Path, worktree: Path) -> None:
    subprocess.run(  # noqa: S603  # trusted args
        ['git', 'worktree', 'remove', '--force', str(worktree)],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    shutil.rmtree(worktree, ignore_errors=True)


def run_compare(
        repo_root: Path,
        base_ref: str,
        profiles: list[str],
        blocks: int,
        work_dir: Path,
        micro: bool = True,
) -> dict[str, Any]:
    """Returns {base_commit, head_commit, profiles: {profile: {op: comparison}}, micro}"""
    head_commit = _git(repo_root, 'rev-parse', 'HEAD')
    base_commit = _git(repo_root, 'merge-base', 'HEAD', base_ref)
    if base_commit == head_commit:
        raise BenchError('base resolves to HEAD itself — nothing to compare')

    cached = {profile: ensure_profile_cached(repo_root, profile) for profile in profiles}
    worktree = _setup_worktree(repo_root, base_commit)
    micro_comparison: dict[str, Any] = {}
    try:
        comparison: dict[str, Any] = {}
        for profile in profiles:
            expected = load_expected(cached[profile], profile)
            samples: dict[str, dict[str, list[float]]] = {'base': {}, 'head': {}}
            for block_index in range(blocks):
                for side, side_root in (('base', worktree), ('head', repo_root)):
                    block = run_block(
                        repo_root=side_root,
                        profile=profile,
                        cached_profile=cached[profile],
                        expected=expected,
                        work_dir=work_dir / side,
                    )
                    for name, duration_ms in block.items():
                        samples[side].setdefault(name, []).append(duration_ms)
                print(f'  [{profile}] block pair {block_index + 1}/{blocks} done')
            comparison[profile] = {
                op: compare_samples(base=base_samples, head=samples['head'][op])
                for op, base_samples in samples['base'].items()
            }

        if micro:  # pure-python micro suite, A/B'd against the same base worktree
            micro_comparison = run_micro_compare(repo_root, worktree, work_dir)
            print('  micro-benchmark comparison done')
    finally:
        _teardown_worktree(repo_root, worktree)

    return {
        'base_commit': base_commit,
        'base_ref': base_ref,
        'head_commit': head_commit,
        'blocks': blocks,
        'profiles': comparison,
        'micro': micro_comparison,
    }
