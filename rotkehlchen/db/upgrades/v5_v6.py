from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.crypto import sha3
from rotkehlchen.errors import DBUpgradeError

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _remove_cache_files(user_data_dir: Path) -> None:
    """At 5->6 version upgrade all cache files should be removed

    That's since we moved all trades in the DB and as such it no longer makes
    any sense to have the cache files.
    """
    for p in user_data_dir.glob('*_trades.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in user_data_dir.glob('*_history.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in user_data_dir.glob('*_deposits_withdrawals.json'):
        try:
            p.unlink()
        except OSError:
            pass

    try:
        (user_data_dir / 'ethereum_tx_log.json').unlink()
    except OSError:
        pass


def _create_new_tables(db: 'DBHandler') -> None:
    # Create the trade type table that's added in this upgrade
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS trade_type (
    type    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* Buy Type */
    INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('A', 1);
    /* Sell Type */
    INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('B', 2);
    /* Settlement Buy Type */
    INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('C', 3);
    /* Settlement Sell Type */
    INSERT OR IGNORE INTO trade_type(type, seq) VALUES ('D', 4);""")
    # Create location table that's added in this upgrade
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS location (
    location    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* External */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('A', 1);
    /* Kraken */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('B', 2);
    /* Poloniex */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('C', 3);
    /* Bittrex */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('D', 4);
    /* Binance */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('E', 5);
    /* Bitmex */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('F', 6);
    /* Coinbase */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('G', 7);
    /* Total */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('H', 8);
    /* Banks */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('I', 9);
    /* Blockchain */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('J', 10);
    /* Coinbase Pro */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('K', 11);
    /* Gemini */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('L', 12);
    /* Equities */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('M', 13);
    /* Real estate */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('N', 14);
    /* Commodities */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('O', 15);
    /* Crypto.com */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('P', 16);
    /* Uniswap */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('Q', 17);
    /* Bitstamp */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('R', 18);
    /* Binance US */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('S', 19);
    /* Bitfinex */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('T', 20);
    /* Bitcoin.de */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('U', 21);
    /* ICONOMI */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('V', 22);
    /* KUCOIN */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('W', 23);
    /* BALANCER */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('X', 24);
    /* LOOPRING */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('Y', 25);
    /* FTX */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('Z', 26);
    /* NEXO */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('[', 27);
    /* BlockFI */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('\\', 28);
    /* IndependentReserve */
    INSERT OR IGNORE INTO location(location, seq) VALUES (']', 29);
    /* Gitcoin */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('^', 30);
    /* Sushiswap */
    INSERT OR IGNORE INTO location(location, seq) VALUES ('_', 31);
    """)
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS asset_movement_category (
    category    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* Deposit Category */
    INSERT OR IGNORE INTO asset_movement_category(category, seq) VALUES ('A', 1);
    /* Withdrawal Category */
    INSERT OR IGNORE INTO asset_movement_category(category, seq) VALUES ('B', 2);
    """)
    db.conn.executescript("""
CREATE TABLE IF NOT EXISTS asset_movements (
    id TEXT PRIMARY KEY,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_movement_category(category),
    address TEXT,
    transaction_id TEXT,
    time INTEGER,
    asset TEXT NOT NULL,
    amount TEXT,
    fee_asset TEXT,
    fee TEXT,
    link TEXT
    );""")
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS used_query_ranges (
    name VARCHAR[24] NOT NULL PRIMARY KEY,
    start_ts INTEGER,
    end_ts INTEGER
    );""")
    db.conn.executescript("""
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
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS margin_positions (
    id TEXT PRIMARY KEY,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    open_time INTEGER,
    close_time INTEGER,
    profit_loss TEXT,
    pl_currency TEXT NOT NULL,
    fee TEXT,
    fee_currency TEXT,
    link TEXT,
    notes TEXT
    );""")


def _upgrade_trades_table(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the data trades table at v5
    query = cursor.execute(
        """SELECT time, location, pair, type, amount, rate, fee, fee_currency,
        link, notes FROM trades;""",
    )
    trade_tuples = []
    for result in query:
        # This is the logic of trade addition in v6 of the DB
        time = result[0]
        pair = result[2]
        old_trade_type = result[3]
        # hand deserialize trade type from DB enum since this code is going to stay
        # here even if the deserialization function changes
        if old_trade_type == 'buy':
            trade_type = 'A'
        elif old_trade_type == 'sell':
            trade_type = 'B'
        else:
            raise DBUpgradeError(
                f'Unexpected trade_type "{trade_type}" found while upgrading '
                f'from DB version 5 to 6',
            )

        trade_id = sha3(('external' + str(time) + str(old_trade_type) + pair).encode()).hex()
        trade_tuples.append((
            trade_id,
            time,
            'A',  # Symbolizes external in the location enum
            pair,
            trade_type,
            result[4],
            result[5],
            result[6],
            result[7],
            result[8],
            result[9],
        ))

    # We got all the external trades data. Now delete the old table and create
    # the new one
    cursor.execute('DROP TABLE trades;')
    db.conn.commit()
    # This is the scheme of the trades table at v6 from db/utils.py
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    time INTEGER,
    location VARCHAR[24],
    pair VARCHAR[24],
    type CHAR(1) NOT NULL DEFAULT ('B') REFERENCES trade_type(type),
    amount TEXT,
    rate TEXT,
    fee TEXT,
    fee_currency VARCHAR[10],
    link TEXT,
    notes TEXT
    );""")
    db.conn.commit()

    # and finally move the data to the new table
    cursor.executemany(
        'INSERT INTO trades('
        '  id, '
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        trade_tuples,
    )
    db.conn.commit()


def _location_to_enum_location(location: str) -> str:
    """Serialize location strings to DB location enums

    The reason we have a specialized function here and not just using
    deserialize_location(location).serialize_for_db() is that this code
    should work in the future if either of the two functions change or dissapear.
    """
    if location == 'external':
        return 'A'
    if location == 'kraken':
        return 'B'
    if location == 'poloniex':
        return 'C'
    if location == 'bittrex':
        return 'D'
    if location == 'binance':
        return 'E'
    if location == 'bitmex':
        return 'F'
    if location == 'coinbase':
        return 'G'
    if location == 'total':
        return 'H'
    if location == 'banks':
        return 'I'
    if location == 'blockchain':
        return 'J'
    # else
    raise DBUpgradeError(f'Invalid location {location} encountered during DB v5->v6 upgrade')


def _upgrade_timed_location_data(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the timed location data table at v5
    query = cursor.execute('SELECT time, location, usd_value FROM timed_location_data;')
    tuples = []
    for result in query:
        tuples.append((result[0], _location_to_enum_location(result[1]), result[2]))

    # We got all the old timed location data. Now delete the old table and create
    # the new one
    cursor.execute('DROP TABLE timed_location_data;')
    db.conn.commit()
    # This is the scheme of the timed_location_Data table at v6 from db/utils.py
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timed_location_data (
        time INTEGER,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        usd_value TEXT,
        PRIMARY KEY (time, location)
    );
    """)
    db.conn.commit()

    # and finally move the data to the new table
    cursor.executemany(
        'INSERT INTO timed_location_data(time, location, usd_value)'
        'VALUES (?, ?, ?)',
        tuples,
    )
    db.conn.commit()


def upgrade_v5_to_v6(db: 'DBHandler') -> None:
    """Upgrades the DB from v5 to v6

    - removes all cache files
    - upgrades trades table to use the new id scheme
    - upgrades trades table to use an enum table for trade type
    - upgrades trades table to use an enum table for location
    - upgrades timed_location_data table to use an enum table for location
    """
    _remove_cache_files(db.user_data_dir)
    _create_new_tables(db)
    _upgrade_trades_table(db)
    _upgrade_timed_location_data(db)
