import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


NEW_BASE_ENTRY_FIELDS_COUNT = 12


def _update_history_events_schema(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """
    1. Rewrite the DB schema of the history events to have subtype as non Optional
    2. Delete counterparty and extra_data fields

    Also turn all null subtype entries to have subtype none
    """
    log.debug('Enter _update_history_events_schema')
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS history_events_copy (
    identifier INTEGER NOT NULL PRIMARY KEY,
    event_identifier BLOB NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(event_identifier, sequence_index)
    );""")
    new_entries = []
    with conn.read_ctx() as read_cursor:
        read_cursor.execute('SELECT * from history_events')

        for entry in read_cursor:
            if entry[11] is None:
                new_entries.append(entry[:NEW_BASE_ENTRY_FIELDS_COUNT - 1] + ('none',))  # turn NULL values to text `none`  # noqa: E501
            else:
                new_entries.append(entry[:NEW_BASE_ENTRY_FIELDS_COUNT])  # Don't change NON-NULL values  # noqa: E501

    write_cursor.executemany('INSERT INTO history_events_copy VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_entries)  # noqa: E501
    write_cursor.execute('DROP TABLE history_events')
    write_cursor.execute('ALTER TABLE history_events_copy RENAME TO history_events')
    log.debug('Exit _update_history_events_schema')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    """
    Creates evm_events_info table and moves there values previously stored in history_events.
    """
    log.debug('Enter _create_new_tables')
    write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_events_info(
            identifier INTEGER PRIMARY KEY,
            counterparty TEXT,
            product TEXT,
            address TEXT,
            extra_data TEXT,
            FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
    """)  # noqa: E501

    log.debug('Exit _create_new_tables')


def upgrade_v36_to_v37(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v36 to v37. This was in v1.28.0 release.

        - Replace null history event subtype
    """
    log.debug('Entered userdb v36->v36 upgrade')
    progress_handler.set_total_steps(2)
    with db.user_write() as write_cursor:
        _update_history_events_schema(write_cursor, db.conn)
        progress_handler.new_step()
        _create_new_tables(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v36->v36 upgrade')
