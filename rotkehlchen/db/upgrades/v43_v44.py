import logging
import re
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def _update_nft_table(write_cursor: 'DBCursor') -> None:
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS nfts_new (
        identifier TEXT NOT NULL PRIMARY KEY,
        name TEXT,
        last_price TEXT NOT NULL,
        last_price_asset TEXT NOT NULL,
        manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
        owner_address TEXT,
        blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
        is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
        image_url TEXT,
        collection_name TEXT,
        usd_price REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
        FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
        FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")  # noqa: E501
    write_cursor.execute(
        'SELECT identifier, name, last_price, last_price_asset, manual_price, owner_address, '
        'is_lp, image_url, collection_name, usd_price FROM nfts',
    )
    final_rows = []
    for row in write_cursor:
        final_row = list(row)
        if row[2] is None:
            final_row[2] = 0  # set last_price to a default of 0
        if row[3] is None:
            final_row[3] = 'ETH'  # set default asset to ethereum if missing for last_price_asset

        final_rows.append(final_row)

    write_cursor.executemany(
        'INSERT OR IGNORE INTO nfts_new(identifier, name, last_price, last_price_asset, '
        'manual_price, owner_address, is_lp, image_url, collection_name, usd_price) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        final_rows,
    )
    write_cursor.execute('DROP TABLE nfts')
    write_cursor.execute('ALTER TABLE nfts_new RENAME TO nfts')


@enter_exit_debug_log()
def _remove_log_removed_column(write_cursor: 'DBCursor') -> None:
    write_cursor.execute(
        'ALTER TABLE evmtx_receipt_logs DROP COLUMN removed;',
    )


def _upgrade_account_tags(write_cursor: 'DBCursor') -> None:
    """Upgrade the object_reference references in tag_mappings to not
    depend on the supported blockchain since the format has changed in 1.35
    """
    object_references: list[tuple[str, str]] = write_cursor.execute(
        'SELECT object_reference, tag_name FROM tag_mappings',
    ).fetchall()
    if len(object_references) == 0:
        return

    remove_keys, insert_entries = [], set()
    supported_blockchains = re.compile('^(ETH|ETH2|BTC|BCH|KSM|AVAX|DOT|OPTIMISM|POLYGON_POS|ARBITRUM_ONE|BASE|GNOSIS|SCROLL|ZKSYNC_LITE)')  # noqa: E501  # supported blockchains at v1.35
    for (object_reference, tag_name) in object_references:
        new_object_reference, count = supported_blockchains.subn('', object_reference)
        if count != 0:
            remove_keys.append((object_reference,))
            insert_entries.add((new_object_reference, tag_name))

    write_cursor.executemany('DELETE FROM tag_mappings WHERE object_reference=?', remove_keys)
    write_cursor.executemany(
        'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)',
        list(insert_entries),
    )


@enter_exit_debug_log(name='UserDB v43->v44 upgrade')
def upgrade_v43_to_v44(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v42 to v43. This was in v1.35 release.

    - add usd_price to the nfts table
    """
    progress_handler.set_total_steps(4)
    with db.user_read_write() as write_cursor:
        _update_nft_table(write_cursor)
        progress_handler.new_step()
        _remove_log_removed_column(write_cursor)
        progress_handler.new_step()
        _upgrade_account_tags(write_cursor)
        progress_handler.new_step()

    db.conn.execute('VACUUM;')
    progress_handler.new_step()
