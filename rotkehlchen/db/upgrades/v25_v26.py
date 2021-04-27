from typing import TYPE_CHECKING

from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from sqlite3 import Cursor

    from rotkehlchen.db.dbhandler import DBHandler


class V25V26UpgradeHelper():

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.msg_aggregator = msg_aggregator
        self.v25exchangename_to_location = {
            'kraken': 'B',
            'poloniex': 'C',
            'bittrex': 'D',
            'bitmex': 'F',
            'binance': 'E',
            'coinbase': 'G',
            'coinbasepro': 'K',
            'gemini': 'L',
            'bitstamp': 'R',
            'binance_us': 'S',
            'bitfinex': 'T',
            'bitcoinde': 'U',
            'iconomi': 'V',
            'kucoin': 'W',
            'ftx': 'Z',
            'rotkehlchen': 'A',
        }

    def upgrade_user_credentials(self, cursor: 'Cursor') -> None:
        # get old data
        query = cursor.execute(
            'SELECT name, api_key, api_secret, passphrase FROM user_credentials;',
        )
        old_tuples = query.fetchall()
        # upgrade table
        cursor.execute('DROP TABLE IF EXISTS user_credentials;')
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_credentials (
        name TEXT NOT NULL,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        api_key TEXT,
        api_secret TEXT,
        passphrase TEXT,
        PRIMARY KEY (name, location)
        );""")
        # upgrade data and insert to the newtable
        new_tuples = []
        for entry in old_tuples:
            location = self.v25exchangename_to_location.get(entry[0])
            if location is None:
                self.msg_aggregator.add_warning(
                    f'During v25 -> v26 DB upgrade found unexpected user credentials for '
                    f'{entry[0]} in the DB. These credentials will not be moved to the new DB',
                )
                continue

            new_tuples.append((
                'rotkehlchen' if location == 'A' else entry[0],  # name
                location,
                entry[1],  # api key
                entry[2],  # api secret
                entry[3],  # passphrase
            ))

        cursor.executemany(
            'INSERT OR IGNORE INTO user_credentials('
            'name, location, api_key, api_secret, passphrase'
            ') VALUES(?, ?, ?, ?, ?);',
            new_tuples,
        )


def upgrade_v25_to_v26(db: 'DBHandler') -> None:
    """Upgrades the DB from v25 to v26

    - Upgrades the user_credentials table to have a name and location
    """
    helper = V25V26UpgradeHelper(db.msg_aggregator)
    cursor = db.conn.cursor()
    helper.upgrade_user_credentials(cursor)
    del helper
    db.conn.commit()
