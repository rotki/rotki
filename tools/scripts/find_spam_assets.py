"""
Find spam assets in rotki's global database.

This script searches for EVM tokens marked with protocol='spam' in the global.db
and outputs them in JSON format compatible with the spam asset updates in the
rotki/data repository: https://github.com/rotki/data/tree/main/updates/spam_assets

Usage:
    # Print to stdout
    uv run python tools/scripts/find_spam_assets.py

    # Write to file
    uv run python tools/scripts/find_spam_assets.py --output spam_assets.json

    # Use custom data directory
    uv run python tools/scripts/find_spam_assets.py --data-directory /path/to/data
"""

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import SPAM_PROTOCOL, ChainID

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

DATA_DIR_NAMES = ('data', 'develop_data')


def get_data_directories(custom_data_dir: Path | None) -> list[Path]:
    """Return list of data directories to check for global databases."""
    if custom_data_dir is not None:
        if custom_data_dir.exists():
            return [custom_data_dir]
        log.warning(f'Provided data directory does not exist: {custom_data_dir}')
        return []

    base_dir = default_data_directory().parent
    directories = [base_dir / name for name in DATA_DIR_NAMES if (base_dir / name).exists()]

    if not directories:
        log.warning(f'No data directories found in {base_dir}')

    return directories


def get_spam_assets_from_db(db_path: Path) -> dict[str, dict[str, str | int]]:
    """Query spam assets from a global database."""
    spam_assets: dict[str, dict[str, str | int]] = {}
    query = """
        SELECT e.identifier, e.address, a.name, c.symbol, e.decimals, e.chain
        FROM evm_tokens e
        JOIN assets a ON e.identifier = a.identifier
        JOIN common_asset_details c ON e.identifier = c.identifier
        WHERE e.protocol = ?
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (SPAM_PROTOCOL,))
            for identifier, address, name, symbol, decimals, chain_id in cursor:
                try:
                    chain_name = ChainID.deserialize(chain_id).to_name()
                except DeserializationError as e:
                    log.warning(
                        f'Unknown chain ID {chain_id} for token {address}: {e!s}, skipping',
                    )
                    continue

                spam_assets[identifier] = {
                    'address': address,
                    'name': name,
                    'symbol': symbol,
                    'decimals': decimals if decimals is not None else 18,
                    'chain': chain_name,
                }
    except sqlite3.Error as e:
        log.error(f'Database error while reading {db_path}: {e}')

    return spam_assets


def find_all_spam_assets(data_directories: list[Path]) -> list[dict[str, str | int]]:
    """Find all spam assets from global databases in the given data directories."""
    all_spam_assets: dict[str, dict[str, str | int]] = {}
    for data_dir in data_directories:
        if not (db_path := data_dir / GLOBALDIR_NAME / GLOBALDB_NAME).exists():
            log.warning(f'Global database not found: {db_path}')
            continue

        log.info(f'Reading spam assets from: {db_path}')
        all_spam_assets |= get_spam_assets_from_db(db_path)

    return list(all_spam_assets.values())


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Find spam assets in rotki global database(s).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--data-directory',
        type=Path,
        default=None,
        help='Custom data directory path. If not provided, checks both data and develop_data.',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output file path. If not provided, prints to stdout.',
    )

    args = parser.parse_args()
    if not (data_directories := get_data_directories(args.data_directory)):
        log.error('No valid data directories found.')
        sys.exit(1)

    json_output = json.dumps({'spam_assets': find_all_spam_assets(data_directories)}, indent=2)
    if args.output:
        args.output.write_text(json_output)
        log.info(f'Output written to: {args.output}')
        sys.exit(0)

    print(json_output)


if __name__ == '__main__':
    main()
