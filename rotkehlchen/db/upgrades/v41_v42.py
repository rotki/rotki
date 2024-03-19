from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


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
    CREATE TABLE IF NOT EXISTS zksynclite_transactions (
    tx_hash BLOB NOT NULL PRIMARY KEY,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES zksynclite_tx_type(type),
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
    write_cursor.execute(
        'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
        ('n', Location.SCROLL.value),
    )


@enter_exit_debug_log(name='UserDB v41->v42 upgrade')
def upgrade_v41_to_v42(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v41 to v42. This was in v1.33 release.

        - Create new tables for zksync lite
    """
    progress_handler.set_total_steps(2)
    with db.user_write() as write_cursor:
        _add_zksynclite(write_cursor)
        progress_handler.new_step()
        _add_new_supported_locations(write_cursor)
        progress_handler.new_step()
