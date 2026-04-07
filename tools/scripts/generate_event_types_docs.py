"""Generate and verify the event-types.md documentation page.

This script reads the canonical EVENT_CATEGORY_MAPPINGS and EVENT_CATEGORY_DETAILS
from the rotki codebase and either generates a fresh event-types.md page or checks
an existing one for drift.

Usage:
    # Generate the auto-generatable tables to stdout
    python tools/scripts/generate_event_types_docs.py --generate

    # Check an existing file for drift (exit 0 = in sync, exit 1 = diverged)
    python tools/scripts/generate_event_types_docs.py --check path/to/event-types.md

    # Insert markers into an existing event-types.md
    python tools/scripts/generate_event_types_docs.py --add-markers event-types.md -o out.md

    # Update the valid-combinations table in-place
    python tools/scripts/generate_event_types_docs.py --generate --inject file.md -o file.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Final

from rotkehlchen.accounting.constants import (
    DEFAULT,
    EVENT_CATEGORY_DETAILS,
    EVENT_CATEGORY_MAPPINGS,
)
from rotkehlchen.history.events.structures.types import (
    EventCategory,
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)

BEGIN_COMBINATIONS: Final = '<!-- BEGIN:GENERATED:valid-combinations -->'
END_COMBINATIONS: Final = '<!-- END:GENERATED:valid-combinations -->'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ACRONYMS: Final[dict[str, str]] = {
    'Nft': 'NFT',
    'Mev': 'MEV',
}


def _format_enum_name(member: HistoryEventType | HistoryEventSubType) -> str:
    """Convert an enum member name to Title Case with spaces.

    Uses the enum's own __str__() which lowercases and splits on underscore.
    We then title-case each word, preserving well-known acronyms.
    """
    words = str(member).title().split()
    return ' '.join(_ACRONYMS.get(w, w) for w in words)


def _direction_str(direction: EventDirection) -> str:
    return {
        EventDirection.IN: 'In',
        EventDirection.OUT: 'Out',
        EventDirection.NEUTRAL: 'Neutral',
    }[direction]


def _get_label(category: EventCategory) -> str:
    """Get the default UI label for an EventCategory."""
    details_map = EVENT_CATEGORY_DETAILS.get(category, {})
    details = details_map.get(DEFAULT)
    if details is None:
        return str(category)
    return details.label


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate_per_type_tables() -> str:
    """Generate reference markdown tables for each HistoryEventType.

    These tables are for reference only (used by --check to compare against
    existing hand-written docs). They are NOT auto-injected because the docs
    contain hand-written descriptions, examples, and notes around each table.
    """
    lines: list[str] = []

    for event_type in HistoryEventType:
        subtype_map = EVENT_CATEGORY_MAPPINGS.get(event_type)
        if subtype_map is None:
            continue

        lines.extend([
            f'### {_format_enum_name(event_type)}\n',
            '| Subtype | UI Category | Direction | Example |',
            '| --- | --- | --- | --- |',
        ])

        for subtype, cat_map in subtype_map.items():
            default_cat = cat_map[DEFAULT]
            label = _get_label(default_cat)
            direction = _direction_str(default_cat.direction)
            subtype_name = f'`{_format_enum_name(subtype)}`'

            lines.append(
                f'| {subtype_name} | {label} | {direction} |  |',
            )

        lines.append('')

    return '\n'.join(lines)


def _pad_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format a markdown table with aligned/padded columns."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def fmt_row(cells: list[str]) -> str:
        padded = [cell.ljust(col_widths[i]) for i, cell in enumerate(cells)]
        return '| ' + ' | '.join(padded) + ' |'

    sep = '| ' + ' | '.join('-' * w for w in col_widths) + ' |'
    lines = [fmt_row(headers), sep]
    lines.extend(fmt_row(row) for row in rows)
    return '\n'.join(lines) + '\n'


def generate_combinations_table() -> str:
    """Generate the summary table of all valid type/subtype combinations."""
    headers = ['Event Type', 'Valid Subtypes']
    rows: list[list[str]] = []

    for event_type in HistoryEventType:
        subtype_map = EVENT_CATEGORY_MAPPINGS.get(event_type)
        if subtype_map is None:
            continue

        type_name = _format_enum_name(event_type)
        subtypes = ', '.join(
            _format_enum_name(sub) for sub in subtype_map
        )
        rows.append([type_name, subtypes])

    return _pad_table(headers, rows)


def generate_full_markdown() -> str:
    """Generate all auto-generatable content with markers."""
    tables = generate_per_type_tables()
    combinations = generate_combinations_table()

    return f"""\
## Reference tables (per event type)

{tables}

{BEGIN_COMBINATIONS}
{combinations}
{END_COMBINATIONS}
"""


def inject_into_existing(existing: str) -> str:
    """Replace the valid-combinations marker section in *existing* with fresh content."""
    combinations = generate_combinations_table()
    return _replace_section(existing, BEGIN_COMBINATIONS, END_COMBINATIONS, combinations)


def _replace_section(text: str, begin: str, end: str, replacement: str) -> str:
    pattern = re.compile(
        re.escape(begin) + r'.*?' + re.escape(end),
        re.DOTALL,
    )
    new_section = f'{begin}\n\n{replacement}\n{end}'
    if pattern.search(text):
        return pattern.sub(new_section, text)
    # markers not found — append
    return text + '\n' + new_section + '\n'


def add_markers_to_existing(content: str) -> str:
    """Insert generation markers into an existing event-types.md that lacks them.

    Only wraps the valid-combinations table (pure data). The per-type tables
    contain hand-written prose and are validated by --check without markers.
    """
    if BEGIN_COMBINATIONS in content:
        return content  # already has markers

    # Find "## All valid type/subtype combinations"
    combos_heading = re.search(
        r'^## All valid type/subtype combinations',
        content, re.MULTILINE,
    )
    if combos_heading is None:
        raise ValueError(
            'Could not find "## All valid type/subtype combinations" heading.',
        )

    # The table starts at the first | after the heading
    combos_after = content[combos_heading.end():]
    table_start_match = re.search(r'^\|', combos_after, re.MULTILINE)
    if table_start_match is None:
        raise ValueError('Could not find the combinations table.')
    combos_table_start = combos_heading.end() + table_start_match.start()

    # Table ends at the first blank line after the table (or next ## heading)
    rest = content[combos_table_start:]
    table_end_match = re.search(r'\n\n', rest)
    combos_table_end = len(content) if table_end_match is None else (
        combos_table_start + table_end_match.start() + 1
    )

    return (
        content[:combos_table_start]
        + BEGIN_COMBINATIONS + '\n\n'
        + content[combos_table_start:combos_table_end]
        + '\n' + END_COMBINATIONS + '\n'
        + content[combos_table_end:]
    )


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------

def _parse_doc_tables(content: str) -> dict[str, dict[str, tuple[str, str]]]:
    """Parse the per-type tables from a docs file by ### headings.

    Returns {type_name: {subtype_name: (ui_category, direction)}}
    """
    result: dict[str, dict[str, tuple[str, str]]] = {}

    current_type: str | None = None
    in_event_types = False
    for line in content.splitlines():
        # Track when we're inside ## Event Types
        if re.match(r'^## Event Types\s*$', line):
            in_event_types = True
            continue
        if re.match(r'^## ', line) and in_event_types:
            break  # next ## section — we're done

        if not in_event_types:
            continue

        # Detect ### headings
        heading = re.match(r'^###\s+(.+)$', line)
        if heading:
            current_type = heading.group(1).strip()
            result[current_type] = {}
            continue

        if current_type is None:
            continue

        # Parse table rows (skip header and separator)
        row = re.match(r'^\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|', line)
        if row:
            subtype = row.group(1).strip()
            ui_cat = row.group(2).strip()
            direction = row.group(3).strip()
            result[current_type][subtype] = (ui_cat, direction)

    return result


def _parse_doc_combinations(content: str) -> dict[str, list[str]]:
    """Parse the valid-combinations table from a docs file.

    Returns {type_name: [subtype_name, ...]}
    """
    result: dict[str, list[str]] = {}

    # Try marker-delimited first, fall back to heading-based
    combo_match = re.search(
        re.escape(BEGIN_COMBINATIONS) + r'(.*?)' + re.escape(END_COMBINATIONS),
        content,
        re.DOTALL,
    )
    if combo_match is None:
        # Fall back: find by heading
        combo_match = re.search(
            r'^## All valid type/subtype combinations\s*$(.*?)(?=^## |\Z)',
            content,
            re.MULTILINE | re.DOTALL,
        )
    if combo_match is None:
        return result

    section = combo_match.group(1)
    for line in section.splitlines():
        row = re.match(r'^\|\s*([^|]+)\|\s*([^|]+)\|', line)
        if row:
            type_name = row.group(1).strip()
            subtypes_str = row.group(2).strip()
            if type_name == 'Event Type' or type_name.startswith('---'):
                continue
            result[type_name] = [s.strip() for s in subtypes_str.split(',')]

    return result


# Name normalization for matching docs headings to source enum names
_DOC_HEADING_TO_SOURCE: Final[dict[str, str]] = {
    'Migration (Migrate)': 'Migrate',
    'Transaction to Self': 'Transaction To Self',
    'Multi-Trade': 'Multi Trade',
}


def _normalize_type_name(doc_name: str) -> str:
    """Normalize a docs heading name to match the source format."""
    return _DOC_HEADING_TO_SOURCE.get(doc_name, doc_name)


def check_docs(filepath: str) -> list[str]:
    """Check an existing docs file against the source of truth.

    Returns a list of human-readable difference messages.
    """
    content = Path(filepath).read_text(encoding='utf-8')
    issues: list[str] = []

    # Build source-of-truth lookup
    source_tables: dict[str, dict[str, tuple[str, str]]] = {}
    source_combos: dict[str, list[str]] = {}

    for event_type in HistoryEventType:
        subtype_map = EVENT_CATEGORY_MAPPINGS.get(event_type)
        if subtype_map is None:
            continue
        type_name = _format_enum_name(event_type)
        source_tables[type_name] = {}
        combo_subtypes: list[str] = []
        for subtype, cat_map in subtype_map.items():
            sub_name = _format_enum_name(subtype)
            default_cat = cat_map[DEFAULT]
            label = _get_label(default_cat)
            direction = _direction_str(default_cat.direction)

            source_tables[type_name][sub_name] = (label, direction)
            combo_subtypes.append(sub_name)

        source_combos[type_name] = combo_subtypes

    # Parse docs
    doc_tables_raw = _parse_doc_tables(content)
    doc_combos_raw = _parse_doc_combinations(content)

    # Normalize doc heading names to source names
    doc_tables: dict[str, dict[str, tuple[str, str]]] = {
        _normalize_type_name(k): v for k, v in doc_tables_raw.items()
    }
    doc_combos: dict[str, list[str]] = {
        _normalize_type_name(k): v for k, v in doc_combos_raw.items()
    }

    # Check per-type tables
    for type_name, subtypes in source_tables.items():
        if type_name not in doc_tables:
            issues.append(f'MISSING TYPE in docs: {type_name}')
            continue

        doc_subtypes = doc_tables[type_name]
        for sub_name, (label, direction) in subtypes.items():
            if sub_name not in doc_subtypes:
                issues.append(
                    f'MISSING in docs: {type_name} + {sub_name}',
                )
                continue

            doc_label, doc_dir = doc_subtypes[sub_name]
            if doc_label != label:
                issues.append(
                    f'LABEL MISMATCH: {type_name} + {sub_name} — '
                    f'docs say "{doc_label}" but source says "{label}"',
                )
            if doc_dir != direction:
                issues.append(
                    f'DIRECTION MISMATCH: {type_name} + {sub_name} — '
                    f'docs say "{doc_dir}" but source says "{direction}"',
                )

        # Check for extra subtypes in docs
        issues.extend(
            f'EXTRA in docs (not in source): {type_name} + {sub_name}'
            for sub_name in doc_subtypes
            if sub_name not in subtypes
        )

    # Check for extra types in docs
    issues.extend(
        f'EXTRA TYPE in docs (not in source): {type_name}'
        for type_name in doc_tables
        if type_name not in source_tables
    )

    # Check combinations table
    for type_name, subs in source_combos.items():
        if type_name not in doc_combos:
            issues.append(
                f'MISSING in combinations table: {type_name}',
            )
            continue

        doc_subs = set(doc_combos[type_name])
        src_subs = set(subs)
        issues.extend(
            f'MISSING subtype in combinations table: {type_name} → {s}'
            for s in src_subs - doc_subs
        )
        issues.extend(
            f'EXTRA subtype in combinations table: {type_name} → {s}'
            for s in doc_subs - src_subs
        )

    issues.extend(
        f'EXTRA TYPE in combinations table (not in source): {type_name}'
        for type_name in doc_combos
        if type_name not in source_combos
    )

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate or verify event-types.md documentation.',
        epilog=(
            'Examples:\n'
            '  %(prog)s --generate                      # print generated tables\n'
            '  %(prog)s --generate --inject f.md -o f.md # update combinations in-place\n'
            '  %(prog)s --check docs/event-types.md      # verify existing file\n'
            '  %(prog)s --add-markers f.md -o f.md       # insert markers into existing file\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--generate',
        action='store_true',
        help='Generate the auto-generated sections of event-types.md.',
    )
    group.add_argument(
        '--check',
        metavar='FILE',
        help='Check an existing event-types.md for drift against the source.',
    )
    group.add_argument(
        '--add-markers',
        metavar='FILE',
        help=(
            'Insert generation markers into an existing event-types.md that '
            'does not yet have them. Writes result to --output or stdout.'
        ),
    )
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Write generated output to FILE instead of stdout (only with --generate).',
    )
    parser.add_argument(
        '--inject',
        metavar='FILE',
        help=(
            'Instead of printing bare generated sections, read FILE and replace '
            'only the marker-delimited sections with fresh content. '
            'Result is written to --output or stdout.'
        ),
    )

    args = parser.parse_args()

    if args.add_markers:
        existing = Path(args.add_markers).read_text(encoding='utf-8')
        output = add_markers_to_existing(existing)
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f'Markers added. Written to {args.output}')
        else:
            print(output)
        return 0

    if args.generate:
        if args.inject:
            existing = Path(args.inject).read_text(encoding='utf-8')
            output = inject_into_existing(existing)
        else:
            output = generate_full_markdown()

        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f'Written to {args.output}')
        else:
            print(output)
        return 0

    # --check mode
    issues = check_docs(args.check)
    if not issues:
        print('event-types.md is in sync with the source code.')
        return 0

    print(f'event-types.md is OUT OF SYNC — {len(issues)} issue(s) found:\n')
    for issue in issues:
        print(f'  {issue}')
    print(
        '\nRun: python tools/scripts/generate_event_types_docs.py '
        f'--generate --inject {args.check} -o {args.check}',
    )
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
