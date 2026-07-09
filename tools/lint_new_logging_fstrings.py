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

The diff is taken from the merge-base with the resolved ref to the WORKING TREE, and
untracked python files count as fully added, so uncommitted work is checked locally
exactly like it will be in the PR. In CI the working tree is the PR head commit, so
the result matches the old committed-only behavior there.

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
    merge-base is the most recent commit. A candidate whose merge-base IS HEAD (an
    up-to-date checkout of that branch) is a valid base: the committed diff is empty
    but uncommitted working tree changes are still checked against it. Skipping such
    refs would instead fall back to an older branch (e.g. bugfixes when sitting on
    develop) whose merge-base diff buries the local changes among weeks of already
    merged - and grandfathered - history.
    """
    current_branch = _git('symbolic-ref', '--quiet', '--short', 'HEAD').stdout.strip()
    best_ref: str | None = None
    best_ts = -1
    for ref in DEFAULT_BASE_CANDIDATES:
        if ref == current_branch:  # the checked-out branch itself is not a useful base
            continue
        if _git('rev-parse', '--verify', '--quiet', ref).returncode != 0:
            continue  # ref does not exist in this checkout
        if (merge_base := _git('merge-base', 'HEAD', ref).stdout.strip()) == '':
            continue  # unrelated history
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

    Diffs from the merge-base with `base` to the working tree, so committed, staged
    and unstaged changes are all covered - exactly what would land in the PR once
    committed. Untracked python files are counted as fully added for the same reason.
    """
    merge_base = _git('merge-base', base, 'HEAD').stdout.strip()
    if merge_base == '':  # explicit sha bases (CI) may not share history locally
        merge_base = base
    result = _git('diff', '--unified=0', '--no-color', merge_base, '--', '*.py')
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

    untracked = _git('ls-files', '--others', '--exclude-standard', '--', '*.py')
    for path in untracked.stdout.splitlines():
        if (filepath := Path(REPO_ROOT, path)).is_file():
            with open(filepath, encoding='utf-8') as new_file:
                added[path] = set(range(1, sum(1 for _ in new_file) + 1))

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
