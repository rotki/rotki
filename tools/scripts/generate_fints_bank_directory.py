"""Generate rotki's compact FinTS institution catalog from the registry export."""

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zipfile import ZipFile

BLZ_RE = re.compile(r'^\d{8}$')
# Logos in frontend/app/public/assets/images/protocols, by institution name. The first match wins,
# so a bank that belongs to a group but has its own brand is listed before the group.
NAMED_LOGOS: list[tuple[str, re.Pattern[str]]] = [
    (logo, re.compile(pattern, re.IGNORECASE)) for logo, pattern in (
        ('bank_1822direkt.svg', r'^1822direkt\b'),
        ('bank_bw_bank.svg', r'\(BW-Bank\)'),
        ('bank_dkb.svg', r'\(DKB\)'),
        ('bank_ing.svg', r'^ING-DiBa\b'),
        ('bank_comdirect.svg', r'^comdirect\b'),
        ('bank_consorsbank.png', r'\bConsorsbank\b'),
        ('bank_postbank.svg', r'^Postbank\b'),
        ('bank_targobank.svg', r'^TARGOBANK\b'),
        ('bank_norisbank.svg', r'^norisbank\b'),
        ('bank_triodos.svg', r'^Triodos Bank\b'),
        ('bank_apobank.svg', r'^Deutsche Apotheker- und Ärztebank\b'),
        ('bank_bbbank.svg', r'^BBBank\b'),
        ('bank_deutsche_bank.svg', r'^Deutsche Bank\b'),
        ('bank_commerzbank.svg', r'^Commerzbank\b'),
        ('bank_hypovereinsbank.svg', r'\bHypoVereinsbank\b'),
        ('bank_sparda.svg', r'^Sparda-Bank\b'),
        ('bank_psd.svg', r'^PSD Bank\b'),
    )
]
# A group logo needs the bank's association as well as its name, since a private bank can carry
# a cooperative or savings-bank word in its name without belonging to the group.
GROUP_LOGOS: list[tuple[str, str, re.Pattern[str]]] = [
    ('bank_sparkasse.svg', 'DSGV', re.compile(r'sparkasse|\bspk\b', re.IGNORECASE)),
    ('bank_vr.svg', 'BVR', re.compile(
        r'volks-?bank|raiffeisen|\braiba\b|\bvr\b|\bvr-?bank|\bvb\b|\brb\b|\brvb\b|\bvoba\b',
        re.IGNORECASE,
    )),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Registry ZIP or ISO-8859-1 CSV')
    parser.add_argument('output', type=Path, help='Catalog JSON to write')
    parser.add_argument('--version', required=True, help='Registry version in YYYY-MM-DD format')
    return parser.parse_args()


def read_registry(input_path: Path) -> tuple[list[dict[str, str]], str]:
    source_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    if input_path.suffix.lower() == '.zip':
        with ZipFile(input_path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith('.csv')]
            if len(csv_names) != 1:
                raise ValueError(f'Expected one CSV in {input_path}, found {len(csv_names)}')
            csv_text = archive.read(csv_names[0]).decode('iso-8859-1')
    else:
        csv_text = input_path.read_text(encoding='iso-8859-1')

    return list(csv.DictReader(io.StringIO(csv_text), delimiter=';')), source_hash


def most_common(values: list[str]) -> str:
    counts = Counter(value for value in values if value)
    return counts.most_common(1)[0][0] if counts else ''


def validate_endpoint(endpoint: str) -> None:
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f'Unsafe FinTS endpoint: {endpoint}')


def logo_for(name: str, organisation: str) -> str | None:
    """The packaged logo of an institution, or None for one shown with the generic bank icon."""
    for logo, pattern in NAMED_LOGOS:
        if pattern.search(name):
            return logo
    for logo, group, pattern in GROUP_LOGOS:
        if organisation == group and pattern.search(name):
            return logo
    return None


def build_catalog(rows: list[dict[str, str]], version: str, source_hash: str) -> dict[str, Any]:
    by_blz: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        blz = row.get('BLZ', '').strip()
        endpoint = row.get('PIN/TAN-Zugang URL', '').strip()
        if not blz:
            continue
        if not BLZ_RE.fullmatch(blz):
            raise ValueError(f'Malformed BLZ: {blz}')
        if not endpoint:
            continue
        validate_endpoint(endpoint)
        by_blz[blz].append(row)

    institutions: defaultdict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: {'aliases': set(), 'bank_codes': set(), 'organisations': set()},
    )
    for blz, bank_rows in by_blz.items():
        bank_endpoints = {row['PIN/TAN-Zugang URL'].strip() for row in bank_rows}
        if len(bank_endpoints) != 1:
            raise ValueError(f'Conflicting endpoints for BLZ {blz}: {sorted(bank_endpoints)}')

        name = most_common([row.get('Institut', '').strip() for row in bank_rows])
        if not name:
            raise ValueError(f'Missing institution name for BLZ {blz}')
        matching_rows = [row for row in bank_rows if row.get('Institut', '').strip() == name]
        city = most_common([row.get('Ort', '').strip() for row in matching_rows])
        key = (name, city, bank_endpoints.pop())
        institutions[key]['bank_codes'].add(blz)
        institutions[key]['organisations'].update(
            row.get('Organisation', '').strip() for row in matching_rows
        )
        institutions[key]['aliases'].update(
            row_name
            for row in bank_rows
            if (row_name := row.get('Institut', '').strip()) and row_name != name
        )

    endpoints = sorted({endpoint for _, _, endpoint in institutions})
    endpoint_indices = {endpoint: index for index, endpoint in enumerate(endpoints)}
    banks: list[list[Any]] = []
    logos: defaultdict[str, list[int]] = defaultdict(list)
    for (name, city, endpoint), values in sorted(institutions.items()):
        organisations = values['organisations'] - {''}
        organisation = organisations.pop() if len(organisations) == 1 else ''
        if (logo := logo_for(name, organisation)) is not None:
            logos[logo].append(len(banks))
        bank_codes = sorted(values['bank_codes'])
        record: list[Any] = [
            name,
            city,
            endpoint_indices[endpoint],
            bank_codes[0] if len(bank_codes) == 1 else bank_codes,
        ]
        if values['aliases']:
            record.append(sorted(values['aliases']))
        banks.append(record)

    return {
        'b': banks,
        'e': endpoints,
        'g': dict(sorted(logos.items())),
        'h': source_hash,
        'v': version,
    }


def serialize(value: Any) -> str:
    """JSON with a space inside every object's braces, the layout the frontend linter keeps."""
    if isinstance(value, dict):
        members = ', '.join(f'{json.dumps(key)}: {serialize(item)}' for key, item in value.items())
        return f'{{ {members} }}'
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    args = parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.version):
        raise ValueError('Version must use YYYY-MM-DD format')
    rows, source_hash = read_registry(args.input)
    catalog = build_catalog(rows, args.version, source_hash)
    args.output.write_text(f'{serialize(catalog)}\n', encoding='utf-8')


if __name__ == '__main__':
    main()
