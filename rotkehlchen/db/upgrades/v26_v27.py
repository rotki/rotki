from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v26_to_v27(db: 'DBHandler') -> None:
    """Upgrades the DB from v26 to v27

    - Deletes and recreates the tables that were changed after removing UnknownEthereumToken
    """
    cursor = db.conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS balancer_events;')
    cursor.execute("""
CREATE TABLE IF NOT EXISTS balancer_events (
    tx_hash VARCHAR[42] NOT NULL,
    log_index INTEGER NOT NULL,
    address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    type TEXT NOT NULL,
    pool_address_token TEXT NOT NULL,
    lp_amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    amount0 TEXT NOT NULL,
    amount1 TEXT NOT NULL,
    amount2 TEXT,
    amount3 TEXT,
    amount4 TEXT,
    amount5 TEXT,
    amount6 TEXT,
    amount7 TEXT,
    FOREIGN KEY (pool_address_token) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);
""")
    cursor.execute('DROP TABLE IF EXISTS balancer_pools;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "balancer_events%";')

    cursor.execute('DROP TABLE IF EXISTS amm_swaps;')
    cursor.execute("""
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
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);""")
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "balancer_trades%";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "uniswap_trades%";')

    cursor.execute('DROP TABLE IF EXISTS uniswap_events;')
    cursor.execute("""
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
    FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
    PRIMARY KEY (tx_hash, log_index)
);""")
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "uniswap_events%";')

    db.conn.commit()
