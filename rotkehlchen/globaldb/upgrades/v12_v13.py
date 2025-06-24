import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v12->v13 upgrade')
def migrate_to_v13(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Add new token kinds (SPL Tokens & NFTs) for the solana ecosystem.
    - Add solana_tokens table and migrate solana tokens to that.

    This upgrade takes place in v1.40.0"""
    @progress_step('Add new token kinds for Solana')
    def _update_token_kinds_to_include_solana(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
            /* SPL TOKEN */
            INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('D', 4);
            /* SPL NFT */
            INSERT OR IGNORE INTO token_kinds(token_kind, seq) VALUES ('E', 5);
        """)

    @progress_step('Add solana tokens table and populate from CSV')
    def _add_and_populate_solana_tokens(write_cursor: 'DBCursor') -> None:
        """Create solana tokens table and update asset identifiers to use new solana format"""
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS solana_tokens (
            identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
            token_kind CHAR(1) NOT NULL DEFAULT('D') REFERENCES token_kinds(token_kind),
            address VARCHAR[44] NOT NULL,
            decimals INTEGER,
            protocol TEXT,
            FOREIGN KEY(identifier) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        )""")  # noqa: E501

        dir_path = Path(__file__).resolve().parent.parent.parent
        if (csv_file := dir_path / 'data' / 'solana_tokens_data.csv').exists() is False:
            log.error(f'Missing required CSV file at {csv_file}. This should not happen. Bailing...')  # noqa: E501
            return

        asset_updates, solana_tokens_data = [], []
        duplicated_tokens = ('TRISIG', 'HODLSOL')  # TRISIG maps to TRISG & HODLSOL maps to HODL
        with csv_file.open(encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (old_id := row['old_id']) in duplicated_tokens:  # skip duplicate mapping
                    continue

                asset_updates.append(((new_id := f'solana/token:{row["address"]}'), old_id))
                solana_tokens_data.append((
                    new_id,
                    'D',  # spl token
                    row['address'],
                    row['decimals'],
                    None,
                ))

        write_cursor.switch_foreign_keys('OFF')
        write_cursor.executemany('INSERT INTO solana_tokens(identifier, token_kind, address, decimals, protocol) VALUES(?, ?, ?, ?, ?)', solana_tokens_data)  # noqa: E501
        write_cursor.executemany('UPDATE assets SET identifier = ? WHERE identifier = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE common_asset_details SET identifier = ? WHERE identifier = ?', asset_updates)  # noqa: E501

        # duplicates were skipped during `solana_tokens` creation to avoid unique constraint errors
        # but we still need to update any existing foreign key references to these old identifiers
        asset_updates.extend([
            ('solana/token:BLDiYcvm3CLcgZ7XUBPgz6idSAkNmWY6MBbm8Xpjpump', 'TRISIG'),
            ('solana/token:58UC31xFjDJhv1NnBF73mtxcsxN92SWjhYRzbfmvDREJ', 'HODLSOL'),
        ])
        write_cursor.executemany('UPDATE asset_collections SET main_asset = ? WHERE main_asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE multiasset_mappings SET asset = ? WHERE asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE user_owned_assets SET asset_id = ? WHERE asset_id = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE price_history SET from_asset = ? WHERE from_asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE price_history SET to_asset = ? WHERE to_asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE binance_pairs SET base_asset = ? WHERE base_asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE binance_pairs SET quote_asset = ? WHERE quote_asset = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE counterparty_asset_mappings SET local_id = ? WHERE local_id = ?', asset_updates)  # noqa: E501
        write_cursor.executemany('UPDATE location_asset_mappings SET local_id = ? WHERE local_id = ?', asset_updates)  # noqa: E501
        write_cursor.switch_foreign_keys('ON')
        write_cursor.execute('CREATE INDEX IF NOT EXISTS idx_solana_tokens_identifier ON solana_tokens (identifier, protocol);')  # noqa: E501

        # delete the known duplicates.
        write_cursor.execute('DELETE FROM assets WHERE identifier IN (?, ?)', duplicated_tokens)

    perform_globaldb_upgrade_steps(connection, progress_handler)
