"""Block driver: one block = fresh profile copy → boot → unlock → operations.

Every block starts from a pristine copy of the cached profile so unlock is
always measured cold and one block's mutations can't leak into the next.

Within a block each operation gets one warmup pass and then OP_INNER_PASSES
timed passes of which the MINIMUM is the block's sample. Contention noise
(background tasks firing mid-measurement, scheduler interference) is strictly
one-sided additive, so the minimum is robust against it while a real
regression raises the minimum itself. This was motivated by the synthetic
regression test on PR #12405, where single-pass sampling produced both a
false negative (high-variance op absorbing a real +250ms) and a false
positive (an op bimodal between ~125ms and ~830ms depending on where in the
block it landed relative to post-unlock background-task activity).
boot_to_ping and user_unlock are cold-path by definition and contribute one
sample per block.
"""
import json
import shutil
import subprocess  # noqa: S404
import time
from pathlib import Path
from typing import Any, Final

from tools.bench.operations import OPERATIONS
from tools.bench.runner import BackendRunner, BenchError
from tools.scenarios.base import USER_PASSWORD
from tools.scenarios.cache import cached_profile_path, compute_cache_key, materialize

OP_INNER_PASSES: Final = 3


def ensure_profile_cached(head_repo_root: Path, profile: str) -> Path:
    """Build (or fetch from cache) a profile using the HEAD checkout's
    generator. Runs as a subprocess so the build's GlobalDBHandler singleton
    never enters this process."""
    key = compute_cache_key(profile)
    if (cached := cached_profile_path(key)) is not None:
        return cached
    result = subprocess.run(  # noqa: S603  # trusted args
        ['uv', 'run', 'python', '-m', 'tools.scenarios', 'build', '--profile', profile],  # noqa: S607
        cwd=head_repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise BenchError(f'profile build for {profile} failed:\n{result.stderr}')
    if (cached := cached_profile_path(key)) is None:
        raise BenchError(f'profile build for {profile} reported success but cache is missing')
    return cached


def load_expected(cached_profile: Path, profile: str) -> dict[str, Any]:
    return json.loads(
        (cached_profile / 'users' / profile / 'expected.json').read_text(encoding='utf-8'),
    )


def run_block(
        repo_root: Path,
        profile: str,
        cached_profile: Path,
        expected: dict[str, Any],
        work_dir: Path,
) -> dict[str, float]:
    """Run one measurement block against the backend of the given checkout.
    Returns operation name → duration in ms."""
    data_dir = work_dir / 'data'
    if data_dir.exists():
        shutil.rmtree(data_dir)
    materialize(cached_profile, data_dir)

    timings: dict[str, float] = {}
    with BackendRunner(
        repo_root=repo_root,
        data_dir=data_dir,
        log_dir=work_dir / 'logs',
    ) as backend:
        timings['boot_to_ping'] = backend.start()
        start = time.perf_counter()
        backend.request('POST', f'/users/{profile}', {
            'password': USER_PASSWORD,
            'sync_approval': 'no',
            'resume_from_backup': False,
        })
        timings['user_unlock'] = (time.perf_counter() - start) * 1000

        operations = [op for op in OPERATIONS if profile in op.profiles]
        for operation in operations:  # warmup pass
            operation.run(backend, expected)
        for operation in operations:  # timed passes; min is the sample (see module docstring)
            passes = []
            for _ in range(OP_INNER_PASSES):
                start = time.perf_counter()
                operation.run(backend, expected)
                passes.append((time.perf_counter() - start) * 1000)
            timings[operation.name] = min(passes)

    shutil.rmtree(data_dir)
    return timings


def run_profile(
        repo_root: Path,
        profile: str,
        cached_profile: Path,
        blocks: int,
        work_dir: Path,
        label: str = '',
) -> dict[str, list[float]]:
    """Run the given number of blocks and aggregate samples per operation"""
    expected = load_expected(cached_profile, profile)
    samples: dict[str, list[float]] = {}
    for block_index in range(blocks):
        block = run_block(
            repo_root=repo_root,
            profile=profile,
            cached_profile=cached_profile,
            expected=expected,
            work_dir=work_dir,
        )
        for name, duration_ms in block.items():
            samples.setdefault(name, []).append(duration_ms)
        print(f'  [{label or profile}] block {block_index + 1}/{blocks} done')
    return samples
