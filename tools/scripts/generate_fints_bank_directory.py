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
        lambda: {'aliases': set(), 'bank_codes': set()},
    )
    for blz, bank_rows in by_blz.items():
        endpoints = {row['PIN/TAN-Zugang URL'].strip() for row in bank_rows}
        if len(endpoints) != 1:
            raise ValueError(f'Conflicting endpoints for BLZ {blz}: {sorted(endpoints)}')

        name = most_common([row.get('Institut', '').strip() for row in bank_rows])
        if not name:
            raise ValueError(f'Missing institution name for BLZ {blz}')
        matching_rows = [row for row in bank_rows if row.get('Institut', '').strip() == name]
        city = most_common([row.get('Ort', '').strip() for row in matching_rows])
        key = (name, city, endpoints.pop())
        institutions[key]['bank_codes'].add(blz)
        institutions[key]['aliases'].update(
            row_name
            for row in bank_rows
            if (row_name := row.get('Institut', '').strip()) and row_name != name
        )

    endpoints = sorted({endpoint for _, _, endpoint in institutions})
    endpoint_indices = {endpoint: index for index, endpoint in enumerate(endpoints)}
    banks: list[list[Any]] = []
    for (name, city, endpoint), values in sorted(institutions.items()):
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

    return {'b': banks, 'e': endpoints, 'h': source_hash, 'v': version}


def main() -> None:
    args = parse_args()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.version):
        raise ValueError('Version must use YYYY-MM-DD format')
    rows, source_hash = read_registry(args.input)
    catalog = build_catalog(rows, args.version, source_hash)
    serialized = json.dumps(catalog, ensure_ascii=False)
    args.output.write_text(
        f'{{ {serialized[1:-1]} }}\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
