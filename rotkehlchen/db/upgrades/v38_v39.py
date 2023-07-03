
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
        write_cursor.execute(
            'INSERT INTO nfts_new SELECT identifier, name, last_price, last_price_asset, '
            'manual_price, owner_address, is_lp, image_url, collection_name FROM nfts')
        write_cursor.execute('DROP TABLE nfts')
        write_cursor.execute('ALTER TABLE nfts_new RENAME TO nfts')

    log.debug('Exit _update_nfts_table')


def _reduce_eventid_size(write_cursor: 'DBCursor') -> None:
    """Reduce the size of history event ids"""
    log.debug('Enter _reduce_eventid_size')
    staking_events = write_cursor.execute(
        'SELECT H.identifier, H.subtype, S.validator_index, S.is_exit_or_blocknumber, '
        'H.timestamp FROM history_events H INNER JOIN eth_staking_events_info S '
        'ON S.identifier=H.identifier',
    ).fetchall()
    updates = []
    for identifier, subtype, validator_index, blocknumber, timestamp in staking_events:
        if subtype == 'remove asset':
            days = int(timestamp / 1000 / 86400)
            updates.append((f'EW_{validator_index}_{days}', identifier))
        elif subtype in ('mev reward', 'block production'):
            updates.append((f'BP1_{blocknumber}', identifier))

    imported_events = write_cursor.execute(
        "SELECT identifier, event_identifier FROM history_events WHERE event_identifier LIKE 'rotki_events_%'",  # noqa: E501
    ).fetchall()
    for identifier, event_identifier in imported_events:
        new_event_identifer = event_identifier.replace('rotki_events_bitcoin_tax_', 'REBTX_').replace('rotki_events_', 'RE_')  # noqa: E501
        updates.append((new_event_identifer, identifier))

    write_cursor.executemany(
        'UPDATE history_events SET event_identifier=? WHERE identifier=?', updates,
    )
    log.debug('Exit _reduce_eventid_size')


def upgrade_v38_to_v39(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v38 to v39. This was in v1.30.0 release.
        - Update NFT table to not use double quotes
        - Reduce size of some event identifiers
    """
    log.debug('Entered userdb v38->v39 upgrade')
    progress_handler.set_total_steps(3)
    with db.user_write() as write_cursor:
        _update_nfts_table(write_cursor)
        progress_handler.new_step()
        _reduce_eventid_size(write_cursor)
        progress_handler.new_step()

    db.conn.execute('VACUUM;')
    progress_handler.new_step()

    log.debug('Finished userdb v38->v39 upgrade')
