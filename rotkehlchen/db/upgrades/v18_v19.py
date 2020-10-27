from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v18_to_v19(db: 'DBHandler') -> None:
    """Upgrades the DB from v18 to v19

    - Deletes all aave historical data and cache since they are going to be requeried via the graph
    - Deletes and recreates the table with the new schema
    https://github.com/rotki/rotki/issues/1494
    - Deletes all poloniex trades/deposit/withdrawals so they can be requeried after #1631
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM aave_events;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
    cursor.execute('DROP TABLE IF EXISTS aave_events;')
    cursor.execute("""
CREATE TABLE IF NOT EXISTS aave_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
    asset1 VARCHAR[12] NOT NULL,
    asset1_amount TEXT NOT NULL,
    asset1_usd_value TEXT NOT NULL,
    asset2 VARCHAR[12],
    asset2amount_borrowrate_feeamount TEXT,
    asset2usd_value_accruedinterest_feeusdvalue TEXT,
    borrow_rate_mode VARCHAR[10],
    PRIMARY KEY (event_type, tx_hash, log_index)
);
""")
    # Delete all poloniex trades/deposits/withdrawals so they can be requeried
    cursor.execute('DELETE FROM trades WHERE location="C";')
    cursor.execute('DELETE FROM asset_movements WHERE location="C";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "poloniex_%";')
    db.conn.commit()
