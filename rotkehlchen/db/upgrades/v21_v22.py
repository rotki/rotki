from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v21_to_v22(db: 'DBHandler') -> None:
    """Upgrades the DB from v21 to v22

    Changes the ETH2 deposit table to properly name the deposit index column
    and transfers all the data to the new table
    """
    cursor = db.conn.cursor()
    query = cursor.execute(
        'SELECT tx_hash, '
        'log_index, '
        'from_address, '
        'timestamp, '
        'pubkey, '
        'withdrawal_credentials, '
        'value, '
        'validator_index from eth2_deposits;',
    )
    entries = []
    for q in query:
        entries.append(q)
    # delete old table and create new one
    cursor.execute('DROP TABLE IF EXISTS eth2_deposits;')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    value TEXT NOT NULL,
    deposit_index INTEGER NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
);""")

    # and finally put all data to the new table
    query = ("""
        INSERT INTO eth2_deposits (
        tx_hash,
        log_index,
        from_address,
        timestamp,
        pubkey,
        withdrawal_credentials,
        value,
        deposit_index
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """)
    cursor.executemany(query, entries)
    db.conn.commit()
