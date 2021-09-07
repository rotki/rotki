from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures import BalanceType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _create_new_tables(db: 'DBHandler') -> None:
    """Create new tables added in this upgrade"""
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS amm_swaps (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    to_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0_in TEXT,
    amount1_in TEXT,
    amount0_out TEXT,
    amount1_out TEXT,
    PRIMARY KEY (tx_hash, log_index)
    );""")
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS uniswap_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address VARCHAR[42] NOT NULL,
    token0_identifier TEXT NOT NULL,
    token1_identifier TEXT NOT NULL,
    amount0 TEXT,
    amount1 TEXT,
    usd_price TEXT,
    lp_amount TEXT,
    PRIMARY KEY (tx_hash, log_index)
    );""")


def upgrade_v20_to_v21(db: 'DBHandler') -> None:
    """Upgrades the DB from v20 to v21

    Upgrades the timed balances to also contain the balance type (category).
    Defaults to ASSET right now, but opens up the way to store liabilities too
    """
    # Create balance category table that's added in this upgrade
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS balance_category (
    category    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* Asset Category */
    INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('A', 1);
    /* Liability Category */
    INSERT OR IGNORE INTO balance_category(category, seq) VALUES ('B', 2);
    """)
    cursor = db.conn.cursor()
    # Get the old data, appending the default value of ASSET for balance category
    query = cursor.execute('SELECT time, currency, amount, usd_value FROM timed_balances;')
    balances = []
    for entry in query:
        balances.append((
            BalanceType.ASSET.serialize_for_db(),  # pylint: disable=no-member
            entry[0],  # time
            entry[1],  # currency
            entry[2],  # amount
            entry[3],  # usd_value
        ))
    # delete old table and create new one
    cursor.execute('DROP TABLE IF EXISTS timed_balances')
    cursor.execute("""
CREATE TABLE IF NOT EXISTS timed_balances (
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
    time INTEGER,
    currency VARCHAR[12],
    amount TEXT,
    usd_value TEXT,
    PRIMARY KEY (time, currency, category)
);
""")
    # And add the old data with the new default value to the new table
    cursor.executemany(
        'INSERT INTO timed_balances(category, time, currency, amount, usd_value) '
        'VALUES (?, ?, ?, ?, ?)',
        balances,
    )
    _create_new_tables(db)
    db.conn.commit()
