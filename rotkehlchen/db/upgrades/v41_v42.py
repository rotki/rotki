import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import ChainID, Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def _add_zksynclite(write_cursor: 'DBCursor') -> None:
    """Add zksynclite related table"""
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS zksynclite_tx_type (
    type    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );""")

    write_cursor.execute("""
    /* Transfer Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('A', 1);""")
    write_cursor.execute("""
    /* Deposit Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('B', 2);""")
    write_cursor.execute("""
    /* Withdraw Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('C', 3);""")
    write_cursor.execute("""
    /* ChangePubKey Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('D', 4);""")
    write_cursor.execute("""
    /* ForcedExit Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('E', 5);""")
    write_cursor.execute("""
    /* FullExit Type */
    INSERT OR IGNORE INTO zksynclite_tx_type(type, seq) VALUES ('F', 6);""")
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS zksynclite_transactions (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES zksynclite_tx_type(type),
    is_decoded INTEGER NOT NULL DEFAULT 0 CHECK (is_decoded IN (0, 1)),
    timestamp INTEGER NOT NULL,
    block_number INTEGER NOT NULL,
    from_address TEXT NULL,
    to_address TEXT,
    token_identifier TEXT NOT NULL,
    amount TEXT NOT NULL,
    fee TEXT,
    FOREIGN KEY(token_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE
    );
    """)


@enter_exit_debug_log()
def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:
    write_cursor.executemany(
        'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
        [('n', Location.SCROLL.value), ('o', Location.ZKSYNC_LITE.value)],
    )


@enter_exit_debug_log()
def _upgrade_evmchains_to_skip_detection(write_cursor: 'DBCursor') -> None:
    """We used to have it only in EVM Chain IDs serialized as names.
    Now turning it into all supported chains due to evmlike introduction"""
    write_cursor.execute("SELECT value from settings WHERE name='evmchains_to_skip_detection'")
    if (result := write_cursor.fetchone()) is None:
        return
    try:
        evmchains_to_skip = json.loads(result[0])
    except json.JSONDecodeError as e:
        log.error(f'During Upgrade could not parse {result[0]} as JSON due to {e}')
        return

    evmchains_to_skip = [ChainID.deserialize_from_name(x) for x in evmchains_to_skip]
    chains_to_skip = [x.to_blockchain().value for x in evmchains_to_skip]
    write_cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        ('evmchains_to_skip_detection', json.dumps(chains_to_skip)),
    )


@enter_exit_debug_log()
def _add_calendar_table(write_cursor: 'DBCursor') -> None:
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS calendar (
    identifier INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    description TEXT,
    counterparty TEXT,
    address TEXT,
    blockchain TEXT,
    FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
    UNIQUE(name, address, blockchain)
    );""")  # noqa: E501


@enter_exit_debug_log(name='UserDB v41->v42 upgrade')
def upgrade_v41_to_v42(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v41 to v42. This was in v1.33 release.

        - Create new tables for zksync lite
        - Add new supported locations
        - Add a new table to handle the calendar
    """
    progress_handler.set_total_steps(4)
    with db.user_write() as write_cursor:
        _add_zksynclite(write_cursor)
        progress_handler.new_step()
        _add_new_supported_locations(write_cursor)
        progress_handler.new_step()
        _upgrade_evmchains_to_skip_detection(write_cursor)
        progress_handler.new_step()
        _add_calendar_table(write_cursor)
        progress_handler.new_step()
