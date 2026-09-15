"""Ratchet that stops a file gaining unclassified user messages.

An `add_error`/`add_warning` without a `classification` reaches the frontend as a bare
sentence it cannot group, the state `UserMessageKey` exists to end. Most emitters predate
it, so rejecting every unclassified call would block unrelated work. Instead, for each
python file under rotkehlchen/ changed against the base ref, the number of unclassified
calls may not grow. Classifying a call, moving one or splitting a handler into branches
that keep the same count never fails; adding one does.

The base ref resolves exactly as in lint_new_logging_fstrings.py, including the skip when
none is available. Run it as `python -m tools.lint_user_message_classification`.
"""

import ast
import sys
from pathlib import Path

from tools.lint_new_logging_fstrings import (
    DEFAULT_BASE_CANDIDATES,
    REPO_ROOT,
    _git,
    resolve_base,
)

EMITTERS = frozenset({'add_error', 'add_warning'})


def _passes_classification(call: ast.Call) -> bool:
    return any(
        keyword.arg == 'classification'
        and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None)
        for keyword in call.keywords
    )


def unclassified_lines(source: str) -> list[int]:
    """Line numbers of the add_error/add_warning calls in `source` without a classification."""
    return sorted(
        node.lineno for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in EMITTERS
        and not _passes_classification(node)
    )


def changed_sources(merge_base: str) -> list[str]:
    """Non-test python files under rotkehlchen/ changed since merge_base, untracked included."""
    tracked = _git(
        'diff', '--name-only', '--diff-filter=AMR', merge_base, '--', 'rotkehlchen/*.py',
    )
    untracked = _git('ls-files', '--others', '--exclude-standard', '--', 'rotkehlchen/*.py')
    return sorted({
        path for path in (tracked.stdout.splitlines() + untracked.stdout.splitlines())
        if '/tests/' not in path and Path(REPO_ROOT, path).is_file()
    })


def main() -> None:
    if (base := resolve_base()) is None:
        print('[lint-user-messages] no base ref available (tried --base/LINT_DIFF_BASE/'
              f'{", ".join(DEFAULT_BASE_CANDIDATES)}); skipping the classification ratchet.')
        sys.exit(0)

    if (merge_base := _git('merge-base', base, 'HEAD').stdout.strip()) == '':
        merge_base = base  # explicit sha bases (CI) may not share history locally

    offending: dict[str, tuple[int, list[int]]] = {}
    for path in changed_sources(merge_base):
        after = unclassified_lines(Path(REPO_ROOT, path).read_text(encoding='utf-8'))
        shown = _git('show', f'{merge_base}:{path}')
        before = unclassified_lines(shown.stdout) if shown.returncode == 0 else []
        if len(after) > len(before):
            offending[path] = (len(before), after)

    if len(offending) == 0:
        sys.exit(0)

    print(
        f'[lint-user-messages] {len(offending)} file(s) gained unclassified user '
        f'messages vs {base}.\nPass a classification from rotkehlchen.user_messages '
        '(BadData, NetworkFailure, ...) so the frontend can group the message. Inside an '
        'exchange use self.add_classified_error, which also fills in the location.\n',
    )
    for path, (before_count, after) in offending.items():
        print(
            f'  {path}: {before_count} -> {len(after)} unclassified, '
            f'at lines {", ".join(str(line) for line in after)}',
        )
    sys.exit(1)


if __name__ == '__main__':
    main()
