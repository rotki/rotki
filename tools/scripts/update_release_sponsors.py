"""Update releases_sponsors.md from the JSON returned by gh release view."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Final

VERSION_RE: Final = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
TIERS: Final = ('🥇 Gold Sponsors', '🥈 Silver Sponsors', '🥉 Bronze Sponsors')
SPONSOR_RE: Final = re.compile(r'.+? \(0x[0-9a-fA-F]{40}\)(?: x[1-9][0-9]*)?')


class NoSponsorsSectionError(ValueError):
    """The release notes have no Our Sponsors section."""


def extract_sponsors(body: str) -> str:
    """Extract and validate sponsor tiers without changing names or addresses."""
    lines = iter(body.splitlines())
    for line in lines:
        if re.fullmatch(r'#{1,6}\s+Our Sponsors\s*', line.strip(), re.IGNORECASE):
            break
    else:
        raise NoSponsorsSectionError('Release notes have no Our Sponsors section')

    tiers: dict[str, list[str]] = {}
    current_tier: str | None = None
    for line in lines:
        normalized = line.strip().replace('**', '').replace('`', '')
        tier_heading = re.sub(r'^#{1,6}\s+', '', normalized)
        if tier_heading in TIERS:
            if tier_heading in tiers:
                raise ValueError(f'Duplicate sponsor tier: {tier_heading}')
            tiers[tier_heading] = []
            current_tier = tier_heading
        elif re.match(r'^#{1,6}\s+', normalized):
            break
        elif normalized in ('', 'This release is sponsored by:'):
            continue
        elif (match := re.fullmatch(r'[-*]\s+(.+)', normalized)) is not None:
            if current_tier is None or SPONSOR_RE.fullmatch(match[1]) is None:
                raise ValueError(f'Invalid sponsor entry: {line}')
            tiers[current_tier].append(f'* {match[1]}')
        else:
            raise ValueError(f'Unexpected sponsor section content: {line}')

    if not tiers or any(not sponsors for sponsors in tiers.values()):
        raise ValueError('Sponsor section is empty or contains an empty tier')

    return '\n\n'.join(
        tier + '\n\n' + '\n'.join(tiers[tier]) for tier in TIERS if tier in tiers
    )


def update_sponsors(document: str, tag: str, body: str) -> str:
    """Replace or insert a minor release, preserving other entries and sorting newest first."""
    if (match := VERSION_RE.fullmatch(version := tag.removeprefix('v'))) is None:
        raise ValueError(f'Invalid release tag: {tag}')
    if match[3] != '0':
        raise ValueError(f'Only minor releases are supported: {tag}')

    sponsors = extract_sponsors(body)
    header, *sections = re.split(r'^## ', document, flags=re.MULTILINE)
    entries: dict[tuple[int, ...], str] = {}
    for section in sections:
        heading, separator, _ = section.partition('\n')
        if not separator or VERSION_RE.fullmatch(heading) is None:
            raise ValueError(f'Invalid existing release heading: {heading}')
        key = tuple(int(part) for part in heading.split('.'))
        if key in entries:
            raise ValueError(f'Duplicate existing release: {heading}')
        entries[key] = f'## {section.rstrip()}'

    entries[tuple(int(part) for part in version.split('.'))] = f'## {version}\n\n{sponsors}'
    return header.rstrip() + '\n\n' + '\n\n'.join(
        entries[key] for key in sorted(entries, reverse=True)
    ) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-json', type=Path, required=True)
    parser.add_argument('--sponsors-file', type=Path, default=Path('releases_sponsors.md'))
    parser.add_argument(
        '--skip-without-sponsors', action='store_true',
        help='Skip releases with no Our Sponsors section (for release edits only)',
    )
    args = parser.parse_args()

    try:
        release = json.loads(args.release_json.read_text(encoding='utf-8'))
        if (
            not isinstance(release, dict) or
            not isinstance(release.get('tagName'), str) or
            not isinstance(release.get('body'), str) or
            release.get('isDraft') is not False or
            release.get('isPrerelease') is not False
        ):
            raise ValueError('Expected a published, stable release with tagName and body')

        original = args.sponsors_file.read_text(encoding='utf-8')
        updated = update_sponsors(original, release['tagName'], release['body'])
        if updated != original:
            args.sponsors_file.write_text(updated, encoding='utf-8')
            print(f'Updated {args.sponsors_file} for {release["tagName"]}')
        else:
            print(f'{args.sponsors_file} already matches {release["tagName"]}')
    except NoSponsorsSectionError as error:
        if not args.skip_without_sponsors:
            print(f'Unable to update release sponsors: {error}', file=sys.stderr)
            return 1
        print(f'Skipping {release["tagName"]}: {error}')
    except (OSError, ValueError) as error:
        print(f'Unable to update release sponsors: {error}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
