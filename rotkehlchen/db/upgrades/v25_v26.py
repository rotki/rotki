from typing import TYPE_CHECKING, Set

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from sqlite3 import Connection, Cursor

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
        globaldb = GlobalDBHandler()
        globaldb_conn = globaldb._conn
        globaldb_cursor = globaldb_conn.cursor()
        query = globaldb_cursor.execute('SELECT identifier from assets;')
        self.all_asset_ids = {x[0] for x in query}

    @staticmethod
    def create_tables(conn: 'Connection') -> None:
        """Create tables that are used in this upgrade"""
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_credentials_mappings (
        credential_name TEXT NOT NULL,
        credential_location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        setting_name TEXT NOT NULL,
        setting_value TEXT NOT NULL,
        FOREIGN KEY(credential_name, credential_location) REFERENCES user_credentials(name, location) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY (credential_name, credential_location, setting_name)
        );""")  # noqa: E501
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
        identifier TEXT NOT NULL PRIMARY KEY
        );
        """)

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

    def _process_asset_identifiers(
            self,
            cursor: 'Cursor',
            asset_ids: Set[str],
            table_name: str,
    ) -> None:
        """Processes the given asset ids of an entry and determines if the entry can be used.

        If an asset can't be found in the global db False is returned and warning logged.
        """
        asset_ids = asset_ids - {None}  # remove empty identifiers
        if asset_ids.issubset(self.all_asset_ids):
            return

        for asset_id in asset_ids:
            if asset_id not in self.all_asset_ids:
                # Add it to the user DB assets, even though it's not in the global DB
                # assets, so the entry is not deleted
                cursor.execute(
                    'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
                    (asset_id,),
                )
                self.all_asset_ids.add(asset_id)
                self.msg_aggregator.add_warning(
                    f'During v25 -> v26 DB upgrade found {table_name} entry of unknown asset '
                    f'{asset_id}. The entry is going to be transferred into the newDB '
                    f'but will need to be fixed using the replace functionality.',
                )
                return

    def upgrade_timed_balances(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT category, time, currency, amount, usd_value FROM timed_balances;',
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS timed_balances;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[2]},
                table_name='timed_balances',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS timed_balances (
            category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
            time INTEGER,
            currency TEXT,
            amount TEXT,
            usd_value TEXT,
            FOREIGN KEY(currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (time, currency, category)
        );
        """)
        cursor.executemany(
            'INSERT INTO timed_balances(category, time, currency, amount, usd_value) '
            'VALUES(?, ?, ?, ?, ?);',
            new_tuples,
        )

    def upgrade_manually_tracked_balances(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT asset, label, amount, location FROM manually_tracked_balances;',
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS manually_tracked_balances;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[0]},
                table_name='manually_tracked_balances',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS manually_tracked_balances (
            asset TEXT NOT NULL,
            label TEXT NOT NULL PRIMARY KEY,
            amount TEXT,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.executemany(
            'INSERT INTO manually_tracked_balances(asset, label, amount, location) '
            'VALUES(?, ?, ?, ?);',
            new_tuples,
        )

    def upgrade_margin_positions(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes FROM margin_positions;',  # noqa: E501
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS margin_positions;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[5], entry[7]},
                table_name='margin_positions',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
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
            notes TEXT,
            FOREIGN KEY(pl_currency) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(fee_currency) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.executemany(
            'INSERT INTO margin_positions('
            'id, location, open_time, close_time, profit_loss, pl_currency, fee, '
            'fee_currency, link, notes'
            ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def upgrade_asset_movements(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT id, location, category, address, transaction_id, time, asset, amount, fee_asset, fee, link FROM asset_movements;',  # noqa: E501
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS asset_movements;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[6], entry[8]},
                table_name='asset_movements',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
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
            link TEXT,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(fee_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.executemany(
            'INSERT INTO asset_movements('
            'id, location, category, address, transaction_id, time, '
            'asset, amount, fee_asset, fee, link'
            ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def upgrade_ledger_actions(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT identifier, timestamp, type, location, amount, asset, rate, rate_asset, link, notes FROM ledger_actions;',  # noqa: E501
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS ledger_actions;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[5], entry[7]},
                table_name='ledger_actions',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ledger_actions (
            identifier INTEGER NOT NULL PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            type CHAR(1) NOT NULL DEFAULT('A') REFERENCES ledger_action_type(type),
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            amount TEXT NOT NULL,
            asset TEXT NOT NULL,
            rate TEXT,
            rate_asset TEXT,
            link TEXT,
            notes TEXT,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(rate_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.executemany(
            'INSERT INTO ledger_actions('
            'identifier, timestamp, type, location, amount, asset, rate, rate_asset, link, notes'
            ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def upgrade_trades(self, cursor: 'Cursor') -> None:
        query = cursor.execute(
            'SELECT id, time, location, base_asset, quote_asset, type, amount, rate, fee, fee_currency, link, notes FROM trades;',  # noqa: E501
        )
        old_tuples = query.fetchall()
        cursor.execute('DROP TABLE IF EXISTS trades;')
        new_tuples = []
        for entry in old_tuples:
            self._process_asset_identifiers(
                cursor=cursor,
                asset_ids={entry[3], entry[4], entry[9]},
                table_name='trades',
            )
            new_tuples.append(entry)

        # create the new table and insert all values into it
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY NOT NULL,
            time INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            base_asset TEXT NOT NULL,
            quote_asset TEXT NOT NULL,
            type CHAR(1) NOT NULL DEFAULT ('A') REFERENCES trade_type(type),
            amount TEXT NOT NULL,
            rate TEXT NOT NULL,
            fee TEXT,
            fee_currency TEXT,
            link TEXT,
            notes TEXT,
            FOREIGN KEY(base_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(quote_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(fee_currency) REFERENCES assets(identifier) ON UPDATE CASCADE
        );
        """)
        cursor.executemany(
            'INSERT INTO trades('
            'id, time, location, base_asset, quote_asset, type, '
            'amount, rate, fee, fee_currency, link, notes'
            ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def introduce_assets_table(self, cursor: 'Cursor') -> None:
        """
        Does the migration to the assets table.
        https://github.com/rotki/rotki/issues/2906
        This is a table containing all assets owned by the user and creates foreign
        key relations from all other tables to it.

        Tables containing asset identifiers. [X] -> should not be deleted and repulled

        - adex_events
        - aave_events
        - yearn_vaults_events
        - ethereum_accounts_details
        - timed_balances [X]
        - manually_tracked_balances [X]
        - margin_positions [X]
        - asset_movements [X]
        - ledger_actions [X]
        - trades [X]

        Tables that are not touched due to the unknown token construct:
        - amm_swaps
        - uniswap_events
        - balancer pools

        -> Remember to also clear relevant used_query_ranges for the deleted tables
        """
        # First populate all assets table with all identifiers of the global db assets
        cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
            [(x,) for x in self.all_asset_ids],
        )
        # Then just drop and recreate tables that can easily be repulled
        cursor.execute('DROP TABLE IF EXISTS adex_events;')
        cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "adex_events%";')
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS adex_events (
            tx_hash VARCHAR[42] NOT NULL,
            address VARCHAR[42] NOT NULL,
            identity_address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            type TEXT NOT NULL,
            pool_id TEXT NOT NULL,
            amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            bond_id TEXT,
            nonce INT,
            slashed_at INTEGER,
            unlock_at INTEGER,
            channel_id TEXT,
            token TEXT,
            log_index INTEGER,
            FOREIGN KEY(token) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, address, type, log_index)
        );
        """)
        cursor.execute('DROP TABLE IF EXISTS aave_events;')
        cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
        cursor.execute("""
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
            FOREIGN KEY(asset1) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(asset2) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (event_type, tx_hash, log_index)
        );
        """)
        cursor.execute('DROP TABLE IF EXISTS yearn_vaults_events;')
        cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "yearn_vaults_events%";')
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS yearn_vaults_events (
            address VARCHAR[42] NOT NULL,
            event_type VARCHAR[10] NOT NULL,
            from_asset TEXT NOT NULL,
            from_amount TEXT NOT NULL,
            from_usd_value TEXT NOT NULL,
            to_asset TEXT NOT NULL,
            to_amount TEXT NOT NULL,
            to_usd_value TEXT NOT NULL,
            pnl_amount TEXT,
            pnl_usd_value TEXT,
            block_number INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            tx_hash VARCHAR[66] NOT NULL,
            log_index INTEGER NOT NULL,
            FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (event_type, tx_hash, log_index)
        );
        """)
        cursor.execute('DELETE FROM ethereum_accounts_details;')

        self.upgrade_timed_balances(cursor)
        self.upgrade_manually_tracked_balances(cursor)
        self.upgrade_margin_positions(cursor)
        self.upgrade_asset_movements(cursor)
        self.upgrade_ledger_actions(cursor)
        self.upgrade_trades(cursor)


def upgrade_v25_to_v26(db: 'DBHandler') -> None:
    """Upgrades the DB from v25 to v26

    - Upgrades the user_credentials table to have a name and location
    - Delete deprecated kraken_account_type from settings.
      If user has a kraken key and that setting, associate them in the new mappings table
    - String representation for 2 locations changed.
      * crypto.com -> cryptocom
      * binance_us -> binanceus

      For that reason we need to purge used query ranges and data of binance_us
    - Delete the unused anonymized logs setting from the DB
    - Introduce assets table and foreign key relationships for assets
    """
    helper = V25V26UpgradeHelper(db.msg_aggregator)
    helper.create_tables(db.conn)
    cursor = db.conn.cursor()
    helper.upgrade_user_credentials(cursor)
    helper.migrate_kraken_account_type(cursor)
    helper.purge_binanceus(cursor)
    cursor.execute('DELETE from settings WHERE name="anonymized_logs";')
    helper.introduce_assets_table(cursor)
    del helper
    db.conn.commit()
