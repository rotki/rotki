import os
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.crypto import sha3
from rotkehlchen.errors import DBUpgradeError

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _remove_cache_files(user_data_dir: str) -> None:
    """At 5->6 version upgrade all cache files should be removed

    That's since we moved all trades in the DB and as such it no longer makes
    any sense to have the cache files.
    """
    for p in Path(user_data_dir).glob('*_trades.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in Path(user_data_dir).glob('*_history.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in Path(user_data_dir).glob('*_deposits_withdrawals.json'):
        try:
            p.unlink()
        except OSError:
            pass

    try:
        os.remove(os.path.join(user_data_dir, 'ethereum_tx_log.json'))
    except OSError:
        pass


def _upgrade_trades_table(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the data trades table had at v5
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


def upgrade_v5_to_v6(db: 'DBHandler') -> None:
    """Upgrades the DB from v5 to v6

    It removes all cache files and also upgrades all trade tables to:
    - use the new id scheme
    - use an enum table for trade type
    - use an enum table for location
    """
    _remove_cache_files(db.user_data_dir)
    _upgrade_trades_table(db)
