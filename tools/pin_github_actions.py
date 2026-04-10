"""Resolve GitHub Actions tags to commit SHAs for hash pinning.

Usage:
    python tools/pin_github_actions.py actions/checkout@v6 [owner/repo@ref ...]
    python tools/pin_github_actions.py --file .github/workflows/rotki_ci.yml

Prints one line per input in the form:
    owner/repo@<full-sha>  # <resolved-tag>

Set GITHUB_TOKEN in the environment to avoid the unauthenticated rate limit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Final
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_ROOT: Final = 'https://api.github.com'
USES_RE: Final = re.compile(r'^\s*(?:-\s*)?uses:\s*([^\s#]+)', re.MULTILINE)


def _request(url: str) -> dict | list:
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'rotki-pin-github-actions',
    }
    if (token := os.environ.get('GITHUB_TOKEN')):
        headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request(url, headers=headers)) as response:  # noqa: S310
        return json.load(response)


def _split_action(action: str) -> tuple[str, str, str]:
    """Split 'owner/repo[/subpath]@ref' into (owner/repo, subpath, ref)."""
    if '@' not in action:
        raise ValueError(f'missing @ref in {action!r}')
    path, ref = action.rsplit('@', 1)
    parts = path.split('/', 2)
    if len(parts) < 2:
        raise ValueError(f'expected owner/repo in {action!r}')
    repo = f'{parts[0]}/{parts[1]}'
    subpath = f'/{parts[2]}' if len(parts) == 3 else ''
    return repo, subpath, ref


def resolve(action: str) -> tuple[str, str]:
    """Return (full_sha, resolved_ref) for an ``owner/repo[/sub]@ref`` spec.

    ``resolved_ref`` is the most specific tag pointing at the SHA when the
    input was a branch or short tag (e.g. ``v6`` → ``v6.0.1``); otherwise it
    is the original ref.
    """
    repo, _, ref = _split_action(action)
    # Try tag first, then branch, then raw commit.
    for endpoint in (f'git/ref/tags/{quote(ref)}', f'git/ref/heads/{quote(ref)}'):
        try:
            data = _request(f'{API_ROOT}/repos/{repo}/{endpoint}')
            break
        except HTTPError as exc:
            if exc.code != 404:
                raise
    else:
        data = _request(f'{API_ROOT}/repos/{repo}/commits/{quote(ref)}')

    if isinstance(data, dict) and 'object' in data:
        obj = data['object']
        sha = obj['sha']
        if obj.get('type') == 'tag':
            # Annotated tag — dereference to the commit it points at.
            tag_obj = _request(f'{API_ROOT}/repos/{repo}/git/tags/{sha}')
            if isinstance(tag_obj, dict):
                sha = tag_obj['object']['sha']
    elif isinstance(data, dict) and 'sha' in data:
        sha = data['sha']
    else:
        raise RuntimeError(f'unexpected response shape for {action!r}')

    resolved_ref = _most_specific_tag(repo, sha, ref)
    return sha, resolved_ref


def _most_specific_tag(repo: str, sha: str, fallback: str) -> str:
    """Find the longest tag name pointing at ``sha`` (e.g. v6 → v6.0.1)."""
    try:
        tags = _request(f'{API_ROOT}/repos/{repo}/tags?per_page=100')
    except HTTPError:
        return fallback
    if not isinstance(tags, list):
        return fallback
    matches = [
        t['name'] for t in tags
        if isinstance(t, dict) and t.get('commit', {}).get('sha') == sha
    ]
    if not matches:
        return fallback
    # Prefer the longest (most specific) name — semver-like tags sort naturally.
    matches.sort(key=len, reverse=True)
    return matches[0]


def format_pinned(action: str, sha: str, resolved_ref: str) -> str:
    repo, subpath, _ = _split_action(action)
    return f'{repo}{subpath}@{sha}  # {resolved_ref}'


def _actions_in_file(path: str) -> list[str]:
    content = Path(path).read_text(encoding='utf-8')
    seen: dict[str, None] = {}
    for match in USES_RE.finditer(content):
        action = match.group(1)
        if action.startswith(('./', '.\\')):
            continue  # local reusable workflow
        if '@' not in action:
            continue
        seen.setdefault(action, None)
    return list(seen)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('actions', nargs='*', help='owner/repo@ref specs to resolve')
    parser.add_argument(
        '--file', '-f',
        action='append',
        default=[],
        help='workflow file to scan for uses: entries',
    )
    args = parser.parse_args()

    targets: list[str] = list(args.actions)
    for file_path in args.file:
        targets.extend(_actions_in_file(file_path))

    if len(targets) == 0:
        parser.error('provide at least one action spec or --file')

    exit_code = 0
    for action in targets:
        try:
            sha, resolved_ref = resolve(action)
        except (HTTPError, ValueError, RuntimeError) as exc:
            print(f'{action}\tERROR: {exc}', file=sys.stderr)
            exit_code = 1
            continue
        print(format_pinned(action, sha, resolved_ref))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
