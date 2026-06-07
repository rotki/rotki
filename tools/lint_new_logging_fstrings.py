#!/usr/bin/env python3
"""Diff-scoped linter that rejects NEW logging f-strings (ruff rule G004).

The codebase still contains many f-string logging calls, so `G004` is globally
ignored in pyproject.toml (enabling it outright would flag ~1500 sites). f-strings
in logging calls are eagerly interpolated even when the log level is disabled, which
wastes work on hot paths. To stop the count from growing while the debt is paid down
incrementally, this check runs ruff's G004 rule but reports a violation only when it
lands on a line ADDED relative to a base git ref. Legacy lines are grandfathered.

Base ref resolution order:
  1. --base <ref> argument
  2. LINT_DIFF_BASE environment variable (CI passes the PR base sha here)
  3. local autodetect: of the known base branches that exist (origin/ and local
     develop, main, bugfixes), pick the one whose merge-base with HEAD is the most
     recent - i.e. the branch this one actually stems from - so a feature branch off
     bugfixes is diffed against bugfixes, not against a stale develop.

If no base can be resolved (e.g. a local checkout without any of those branches), the
check prints a notice and exits 0 so it never blocks local `make lint`.
"""

import json
import os
import re
import subprocess  # noqa: S404
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# base branch names to look for locally, in preference order (origin/<name> first for each)
BASE_BRANCH_NAMES = ('develop', 'main', 'bugfixes')
DEFAULT_BASE_CANDIDATES = tuple(
    f'{prefix}{name}' for name in BASE_BRANCH_NAMES for prefix in ('origin/', '')
)
HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        ['git', *args],  # noqa: S607  # git is expected to be on PATH
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _autodetect_base() -> str | None:
    """Pick the existing base branch closest to HEAD (the one HEAD branched off).

    For each candidate we take its merge-base with HEAD and keep the candidate whose
    merge-base is the most recent commit. Candidates whose merge-base IS HEAD (the
    currently checked-out branch's own ref, or any descendant) are skipped, since
    diffing against them would yield no changes and silently pass.
    """
    head = _git('rev-parse', 'HEAD').stdout.strip()
    current_branch = _git('symbolic-ref', '--quiet', '--short', 'HEAD').stdout.strip()
    best_ref: str | None = None
    best_ts = -1
    for ref in DEFAULT_BASE_CANDIDATES:
        if ref == current_branch:  # the checked-out branch itself is not a useful base
            continue
        if _git('rev-parse', '--verify', '--quiet', ref).returncode != 0:
            continue  # ref does not exist in this checkout
        if (merge_base := _git('merge-base', 'HEAD', ref).stdout.strip()) in ('', head):
            continue  # unrelated history, or ref is at/ahead of HEAD (empty diff)
        if (ts := int(_git('show', '-s', '--format=%ct', merge_base).stdout.strip() or -1)) > best_ts:  # noqa: E501
            best_ts, best_ref = ts, ref
    return best_ref


def resolve_base() -> str | None:
    """Resolve the git ref to diff against, or None if none is available."""
    args = sys.argv[1:]
    if '--base' in args:
        return args[args.index('--base') + 1]
    if (env_base := os.environ.get('LINT_DIFF_BASE')):
        return env_base
    return _autodetect_base()


def added_lines(base: str) -> dict[str, set[int]]:
    """Return {repo_relative_path: {added line numbers}} for python files since base.

    Uses the three-dot diff so only changes introduced on HEAD since the merge-base
    with `base` are considered - exactly what would land in the PR.
    """
    result = _git('diff', '--unified=0', '--no-color', f'{base}...HEAD', '--', '*.py')
    if result.returncode != 0:
        print(f'[lint-new-logs] git diff against {base!r} failed, skipping:\n{result.stderr}')
        return {}

    added: dict[str, set[int]] = {}
    current: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith('+++ b/'):
            current = line[len('+++ b/'):]
            added.setdefault(current, set())
        elif line.startswith('@@') and current is not None and (match := HUNK_RE.match(line)):
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            added[current].update(range(start, start + count))
    return added


def ruff_g004_violations(files: list[str]) -> list[dict]:
    """Run ruff's G004 rule on the given files and return the JSON violations.

    An explicit --select overrides the project-level ignore of G004.
    """
    result = subprocess.run(  # noqa: S603
        ['ruff', 'check', '--select', 'G004', '--no-cache', '--output-format', 'json', *files],  # noqa: S607  # ruff is on PATH under the lint env
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip() == '':
        return []
    return json.loads(result.stdout)


def main() -> None:
    if (base := resolve_base()) is None:
        print('[lint-new-logs] no base ref available (tried --base/LINT_DIFF_BASE/'
              f'{", ".join(DEFAULT_BASE_CANDIDATES)}); skipping diff-scoped G004 check.')
        sys.exit(0)

    added = added_lines(base)
    changed_files = [path for path, lines in added.items() if lines and Path(REPO_ROOT, path).exists()]  # noqa: E501
    if len(changed_files) == 0:
        sys.exit(0)

    offending = [
        violation for violation in ruff_g004_violations(changed_files)
        if (rel := os.path.relpath(violation['filename'], REPO_ROOT)) in added
        and violation['location']['row'] in added[rel]
    ]
    if len(offending) == 0:
        sys.exit(0)

    print(
        f'[lint-new-logs] {len(offending)} new logging f-string(s) introduced vs {base}.\n'
        'Logging f-strings are eagerly interpolated even when the level is disabled. '
        "Use lazy %-args instead, e.g. log.debug('got %s items', len(x)) - or guard "
        'expensive calls with `if log.isEnabledFor(logging.DEBUG):`.\n',
    )
    for violation in offending:
        rel = os.path.relpath(violation['filename'], REPO_ROOT)
        print(f"  {rel}:{violation['location']['row']}: {violation['message']}")
    sys.exit(1)


if __name__ == '__main__':
    main()
