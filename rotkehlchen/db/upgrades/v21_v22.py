from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v21_to_v22(db: 'DBHandler') -> None:
    """Upgrades the DB from v21 to v22

    Changes the ETH2 deposit table to properly name the deposit index column
    and deletes all old data so they can be populated again.
    """
    cursor = db.conn.cursor()
    # delete old table and create new one
    cursor.execute('DROP TABLE IF EXISTS eth2_deposits;')
    cursor.execute('DELETE from used_query_ranges WHERE name LIKE "eth2_deposits_%";')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    deposit_index INTEGER NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
);""")
    db.conn.commit()
