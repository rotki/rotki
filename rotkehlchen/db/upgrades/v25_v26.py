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

    @staticmethod
    def migrate_kraken_account_type(cursor: 'Cursor') -> None:
        settings = cursor.execute(
            'SELECT name, value from settings WHERE name="kraken_account_type";',
        ).fetchone()
        cursor.execute('DELETE from settings WHERE name="kraken_account_type";')
        if settings is None:
            return  # nothing to do

        got_kraken = cursor.execute(
            'SELECT name, location from user_credentials WHERE name=? AND location=?',
            ('kraken', 'B'),
        ).fetchone()
        if got_kraken is None:
            return  # nothing to do

        kraken_account_type = settings[1]
        cursor.execute(
            'INSERT OR IGNORE INTO user_credentials_mappings('
            'credential_name, credential_location, setting_name, setting_value'
            ') VALUES(?, ?, ?, ?);',
            ('kraken', 'B', 'kraken_account_type', kraken_account_type),
        )

    @staticmethod
    def purge_binanceus(cursor: 'Cursor') -> None:
        # Delete the old way of naming binanceus in used query ranges
        cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            ('binance_us\\_%', '\\'),
        )
        cursor.execute('DELETE FROM trades WHERE location = "S";')
        cursor.execute('DELETE FROM asset_movements WHERE location = "S";')


def upgrade_v25_to_v26(db: 'DBHandler') -> None:
    """Upgrades the DB from v25 to v26

    - Upgrades the user_credentials table to have a name and location
    - Delete deprecated kraken_account_type from settings.
      If user has a kraken key and that setting, associate them in the new mappings table
    - String representation for 2 locations changed.
      * crypto.com -> cryptocom
      * binance_us -> binanceus

      For that reason we need to purge used query ranges and data of binance_us
    """
    helper = V25V26UpgradeHelper(db.msg_aggregator)
    cursor = db.conn.cursor()
    helper.upgrade_user_credentials(cursor)
    helper.migrate_kraken_account_type(cursor)
    helper.purge_binanceus(cursor)
    del helper
    db.conn.commit()
