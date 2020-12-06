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
        # here even if deserialize_trade_type_from_db() changes
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
    _upgrade_trades_table(db)
    _upgrade_timed_location_data(db)
