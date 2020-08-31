from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v16_to_v17(db: 'DBHandler') -> None:
    """Upgrades the DB from v16 to v17

    - Deletes all ethereum transactions and query ranges from the DB so they
      can be saved again with the new schema.
    - Deletes ethereum transactions table and creates it with the new schema
      where primary key also includes the from_address
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM ethereum_transactions;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "ethtxs_%";')
    cursor.execute('DROP TABLE IF EXISTS ethereum_transactions;')
    # and create the table. Same schema as was in launch of v1.7.0
    cursor.execute("""
CREATE TABLE IF NOT EXISTS ethereum_transactions (
    tx_hash BLOB,
    timestamp INTEGER,
    block_number INTEGER,
    from_address TEXT,
    to_address TEXT,
    value TEXT,
    gas TEXT,
    gas_price TEXT,
    gas_used TEXT,
    input_data BLOB,
    nonce INTEGER,
    /* we determine uniqueness for ethereum internal transactions by using an
    increasingly negative number */
    PRIMARY KEY (tx_hash, nonce, from_address)
    );""")
