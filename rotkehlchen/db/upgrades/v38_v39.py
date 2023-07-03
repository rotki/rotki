
import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _update_nfts_table(write_cursor: 'DBCursor') -> None:
    """
    Update the nft table to remove double quotes due to https://github.com/rotki/rotki/issues/6368
    """
    log.debug('Enter _update_nfts_table')
    table_exists = write_cursor.execute(
        "SELECT COUNT(*) FROM sqlite_master "
        "WHERE type='table' AND name='evm_internal_transactions'",
    ).fetchone()[0] == 1
    table_to_create = 'nfts'
    if table_exists is True:
        table_to_create += '_new'
    write_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_to_create} (
        identifier TEXT NOT NULL PRIMARY KEY,
        name TEXT,
        last_price TEXT,
        last_price_asset TEXT,
        manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
        owner_address TEXT,
        blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
        is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
        image_url TEXT,
        collection_name TEXT,
        FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
        FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
        FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")  # noqa: E501
    if table_exists is True:
        write_cursor.execute('INSERT INTO nfts_new SELECT * FROM nfts')
        write_cursor.execute('DROP TABLE nfts')
        write_cursor.execute('ALTER TABLE nfts_new RENAME TO nfts')

    log.debug('Exit _update_nfts_table')


def upgrade_v38_to_v39(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v38 to v39. This was in v1.30.0 release.
        - Update NFT table to not use double quotes
        - Reduce size of some event identifiers
    """
    log.debug('Entered userdb v38->v39 upgrade')
    progress_handler.set_total_steps(1)
    with db.user_write() as write_cursor:
        _update_nfts_table(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v38->v39 upgrade')
