from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v23_to_v24(db: 'DBHandler') -> None:
    """Upgrades the DB from v23 to v24

    - Deletes the AdEx used query ranges.
    - Drops the existing AdEx events table.
    - Creates the new AdEx events table that includes `log_index` in the PK.
    """
    cursor = db.conn.cursor()
    # Delete AdEx used query ranges, drop the events table and re-create it
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "adex_events%";')
    cursor.execute('DROP TABLE IF EXISTS adex_events;')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS adex_events (
        tx_hash VARCHAR[42] NOT NULL,
        address VARCHAR[42] NOT NULL,
        identity_address VARCHAR[42] NOT NULL,
        timestamp INTEGER NOT NULL,
        type TEXT NOT NULL,
        pool_id TEXT NOT NULL,
        amount TEXT NOT NULL,
        usd_value TEXT NOT NULL,
        bond_id TEXT,
        nonce INT,
        slashed_at INTEGER,
        unlock_at INTEGER,
        channel_id TEXT,
        token TEXT,
        log_index INTEGER,
        PRIMARY KEY (tx_hash, address, type, log_index));
    """)
    db.conn.commit()
