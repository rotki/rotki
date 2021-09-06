from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _create_new_tables(db: 'DBHandler') -> None:
    """Create new tables added in this upgrade"""
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS aave_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
    asset1 TEXT NOT NULL,
    asset1_amount TEXT NOT NULL,
    asset1_usd_value TEXT NOT NULL,
    asset2 TEXT,
    asset2amount_borrowrate_feeamount TEXT,
    asset2usd_value_accruedinterest_feeusdvalue TEXT,
    borrow_rate_mode VARCHAR[10],
    PRIMARY KEY (event_type, tx_hash, log_index)
    );""")


def upgrade_v14_to_v15(db: 'DBHandler') -> None:
    """Upgrades the DB from v14 to v15

    - Deletes all ethereum transactions from the DB so they can be saved again
      with integers for most numerical fields.
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM ethereum_transactions;')
    _create_new_tables(db)
    db.conn.commit()
