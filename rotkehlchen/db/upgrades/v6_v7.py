from typing import TYPE_CHECKING

from rotkehlchen.crypto import sha3
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.typing import Location, TradeType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _v6_deserialize_location_from_db(symbol: str) -> Location:
    """We copy the deserialize_location_from_db() function at v6

    This is done in case the function ever changes in the future. Also another
    difference is that instead of DeserializationError this throws a DBUpgradeError
    """
    if symbol == 'A':
        return Location.EXTERNAL
    elif symbol == 'B':
        return Location.KRAKEN
    elif symbol == 'C':
        return Location.POLONIEX
    elif symbol == 'D':
        return Location.BITTREX
    elif symbol == 'E':
        return Location.BINANCE
    elif symbol == 'F':
        return Location.BITMEX
    elif symbol == 'G':
        return Location.COINBASE
    elif symbol == 'H':
        return Location.TOTAL
    elif symbol == 'I':
        return Location.BANKS
    elif symbol == 'J':
        return Location.BLOCKCHAIN
    else:
        raise DBUpgradeError(
            f'Failed to deserialize location. Unknown symbol {symbol} for location found in DB',
        )


def _v6_deserialize_trade_type_from_db(symbol: str) -> TradeType:
    """We copy the deserialize_trade_type_from_db() function at v6

    This is done in case the function ever changes in the future. Also another
    difference is that instead of DeserializationError this throws a DBUpgradeError
    """
    if symbol == 'A':
        return TradeType.BUY
    elif symbol == 'B':
        return TradeType.SELL
    elif symbol == 'C':
        return TradeType.SETTLEMENT_BUY
    elif symbol == 'D':
        return TradeType.SETTLEMENT_SELL
    else:
        raise DBUpgradeError(
            f'Failed to deserialize trade type. Unknown DB symbol {symbol} for trade type in DB',
        )


def _upgrade_trades_table(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the data we need from trades table at v6
    query = cursor.execute(
        """SELECT time, location, pair, type, amount, rate, fee, fee_currency,
        link, notes FROM trades;""",
    )
    trade_tuples = []
    for result in query:
        # for each trade get all the relevant data
        time = result[0]
        db_location = result[1]
        pair = result[2]
        db_trade_type = result[3]
        amount = result[4]
        rate = result[5]
        fee = result[6]
        fee_currency = result[7]
        link = result[8]
        notes = result[9]
        # make sure to deserialize the db enums
        location = _v6_deserialize_location_from_db(db_location)
        trade_type = _v6_deserialize_trade_type_from_db(db_trade_type)

        new_trade_id = sha3(
            (str(location) + str(time) + str(trade_type) + pair + amount + rate + link).encode(),
        ).hex()
        trade_tuples.append((
            new_trade_id,
            time,
            db_location,
            pair,
            db_trade_type,
            amount,
            rate,
            fee,
            fee_currency,
            link,
            notes,
        ))

    # We got all the external trades data. Now delete the old table and create
    # the new one
    cursor.execute('DROP TABLE trades;')
    db.conn.commit()
    # This is the scheme of the trades table at v7 from db/utils.py
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    time INTEGER,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
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


def upgrade_v6_to_v7(db: 'DBHandler') -> None:
    """Upgrades the DB from v6 to v7

    - upgrades trades table to use a new id scheme
    """
    _upgrade_trades_table(db)
