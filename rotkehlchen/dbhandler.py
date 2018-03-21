import tempfile
import time
import os
import shutil
from collections import defaultdict
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.utils import ts_now
from rotkehlchen.errors import AuthenticationError, InputError


def str_to_bool(s):
    return True if s == 'True' else False


ROTKEHLCHEN_DB_VERSION = 1


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types
class DBHandler(object):

    def __init__(self, user_data_dir, username, password):
        self.user_data_dir = user_data_dir
        self.connect(password)
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS timed_balances ('
                '    time INTEGER, currency VARCHAR[12], amount DECIMAL, usd_value DECIMAL'
                ')'
            )
        except sqlcipher.DatabaseError:
            raise AuthenticationError('Wrong password while decrypting the database')
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS timed_location_data ('
            '    time INTEGER, location VARCHAR[24], usd_value DECIMAL'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS timed_unique_data ('
            '    time INTEGER, net_usd DECIMAL'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS user_credentials ('
            '    name VARCHAR[24] NOT NULL PRIMARY KEY, api_key TEXT, api_secret TEXT'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS blockchain_accounts ('
            '    blockchain VARCHAR[24], account TEXT NOT NULL PRIMARY KEY'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS eth_tokens ('
            '    token VARCHAR[24] NOT NULL PRIMARY KEY'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS current_balances ('
            '    asset VARCHAR[24] NOT NULL PRIMARY KEY, amount DECIMAL'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS trades ('
            '    id INTEGER PRIMARY KEY ASC,'
            '    time INTEGER,'
            '    location VARCHAR[24],'
            '    pair VARCHAR[24],'
            '    type VARCHAR[3],'
            '    amount DECIMAL,'
            '    rate DECIMAL,'
            '    fee DECIMAL,'
            '    fee_currency VARCHAR[6],'
            '    link TEXT,'
            '    notes TEXT'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS settings ('
            '  name VARCHAR[24] NOT NULL PRIMARY KEY, value TEXT,'
            '  UNIQUE(name, value)'
            ')'
        )
        cursor.execute(
            'INSERT OR IGNORE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(ROTKEHLCHEN_DB_VERSION))
        )
        self.conn.commit()

    def connect(self, password):
        self.conn = sqlcipher.connect(os.path.join(self.user_data_dir, 'rotkehlchen.db'))
        self.conn.text_factory = str
        self.conn.executescript('PRAGMA key="{}"; pragma kdf_iter=64000;'.format(password))
        self.conn.execute('PRAGMA foreign_keys=ON')

    def disconnect(self):
        self.conn.close()

    def export_unencrypted(self, temppath):
        self.conn.executescript(
            'ATTACH DATABASE "{}" AS plaintext KEY "";'
            'SELECT sqlcipher_export("plaintext");'
            'DETACH DATABASE plaintext;'.format(temppath)
        )

    def import_unencrypted(self, unencrypted_db_data, password):
        self.disconnect()
        rdbpath = os.path.join(self.user_data_dir, 'rotkehlchen.db')
        # Make copy of existing encrypted DB before removing it
        shutil.copy2(
            rdbpath,
            os.path.join(self.user_data_dir, 'rotkehlchen_temp_backup.db')
        )
        os.remove(rdbpath)

        # dump the unencrypted data into a temporary file
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdbpath = os.path.join(tmpdirname, 'temp.db')
            with open(tempdbpath, 'wb') as f:
                f.write(unencrypted_db_data)

            # Now attach to the unencrypted DB and copy it to our DB and encrypt it
            self.conn = sqlcipher.connect(tempdbpath)
            self.conn.executescript(
                'ATTACH DATABASE "{}" AS encrypted KEY "{}";'
                'SELECT sqlcipher_export("encrypted");'
                'DETACH DATABASE encrypted;'.format(rdbpath, password)
            )
            self.disconnect()

        self.connect(password)
        # all went okay, remove the original temp backup
        os.remove(os.path.join(self.user_data_dir, 'rotkehlchen_temp_backup.db'))

    def update_last_write(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_write_ts', str(ts_now()))
        )
        self.conn.commit()

    def get_last_write_ts(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('last_write_ts',)
        )
        query = query.fetchall()
        # If setting is not set, it's 0 by default
        if len(query) == 0:
            return 0
        return int(query[0][0])

    def update_last_data_upload_ts(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_data_upload_ts', str(ts_now()))
        )
        self.conn.commit()

    def get_last_data_upload_ts(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('last_data_upload_ts',)
        )
        query = query.fetchall()
        # If setting is not set, it's 0 by default
        if len(query) == 0:
            return 0
        return int(query[0][0])

    def update_premium_sync(self, should_sync):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('premium_should_sync', str(should_sync))
        )
        self.conn.commit()

    def get_premium_sync(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('premium_should_sync',)
        )
        query = query.fetchall()
        # If setting is not set, it's false by default
        if len(query) == 0:
            return False
        return str_to_bool(query[0])

    def get_settings(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT name, value FROM settings;'
        )
        query = query.fetchall()

        settings = {}
        for q in query:
            if q[0] == 'version':
                settings['db_version'] = int(q[1])
            elif q[0] == 'last_write_ts':
                settings['last_write_ts'] = int(q[1])
            elif q[0] == 'premium_should_sync':
                settings['premium_should_sync'] = str_to_bool(q[1])
            elif q[0] == 'last_data_upload_ts':
                settings['last_data_upload_ts'] = int(q[1])
            else:
                settings[q[0]] = q[1]
        return settings

    def add_multiple_balances(self, balances):
        """Execute addition of multiple balances in the DB

        balances should be a list of tuples each containing:
        (time, asset, amount, usd_value)"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT INTO timed_balances('
            '    time, currency, amount, usd_value) '
            ' VALUES(?, ?, ?, ?)',
            balances
        )
        self.conn.commit()
        self.update_last_write()

    def add_multiple_location_data(self, location_data):
        """Execute addition of multiple location data in the DB

        location_data should be a list of tuples each containing:
        (time, location, usd_value)"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT INTO timed_location_data('
            '    time, location, usd_value) '
            ' VALUES(?, ?, ?)',
            location_data
        )
        self.conn.commit()
        self.update_last_write()

    def add_timed_unique_data(self, time, net_usd):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO timed_unique_data(time, net_usd) VALUES (?, ?)',
            (time, net_usd)
        )
        self.conn.commit()
        self.update_last_write()

    def write_owned_tokens(self, tokens):
        """Execute addition of multiple tokens in the DB

        tokens should be a list of token symbols
        (time, location, usd_value)"""
        cursor = self.conn.cursor()
        # Delete previous list and write the new one
        cursor.execute(
            'DELETE FROM eth_tokens;'
        )
        cursor.executemany(
            'INSERT INTO eth_tokens(token) VALUES (?)',
            [(t,) for t in tokens]
        )
        self.conn.commit()
        self.update_last_write()

    def get_owned_tokens(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT token FROM eth_tokens;'
        )
        query = query.fetchall()
        return [q[0] for q in query]

    def add_blockchain_account(self, blockchain, account):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (blockchain, account)
        )
        self.conn.commit()
        self.update_last_write()

    def remove_blockchain_account(self, blockchain, account):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', (blockchain, account)
        )
        self.conn.commit()
        self.update_last_write()

    def add_fiat_balance(self, currency, amount):
        cursor = self.conn.cursor()
        # We don't care about previous value so this simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO current_balances(asset, amount) VALUES (?, ?)',
            (currency, amount)
        )
        self.conn.commit()
        self.update_last_write()

    def remove_fiat_balance(self, currency):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM current_balances WHERE asset = ?;', (currency,)
        )
        self.conn.commit()
        self.update_last_write()

    def get_fiat_balances(self):
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT asset, amount FROM current_balances;'
        )
        query = query.fetchall()

        result = {}
        for entry in query:
            result[entry[0]] = entry[1]
        return result

    def get_blockchain_accounts(self):
        """Returns a dictionary with keys being blockchains and values being
        lists of accounts"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;'
        )
        query = query.fetchall()
        result = defaultdict(list)

        for entry in query:
            if entry[0] not in result:
                result[entry[0]] = []

            result[entry[0]].append(entry[1])

        return result

    def remove(self):
        cursor = self.conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS timed_balances')
        cursor.execute('DROP TABLE IF EXISTS timed_location_data')
        cursor.execute('DROP TABLE IF EXISTS timed_unique_data')
        self.conn.commit()

    def write_balances_data(self, data):
        ts = int(time.time())
        balances = []
        locations = []

        for key, val in data.items():
            if key in ('location', 'net_usd'):
                continue

            balances.append((
                ts,
                key,
                str(val['amount']),
                str(val['usd_value']),
            ))

        for key, val in data['location'].items():
            locations.append((
                ts, key, str(val['usd_value'])
            ))

        self.add_multiple_balances(balances)
        self.add_multiple_location_data(locations)
        self.add_timed_unique_data(ts, str(data['net_usd']))

    def add_exchange(self, name, api_key, api_secret):
        if name not in SUPPORTED_EXCHANGES:
            raise InputError('Unsupported exchange {}'.format(name))

        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO user_credentials (name, api_key, api_secret) VALUES (?, ?, ?)',
            (name, api_key, api_secret)
        )
        self.conn.commit()
        self.update_last_write()

    def remove_exchange(self, name):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM user_credentials WHERE name =?', (name,)
        )
        self.conn.commit()
        self.update_last_write()

    def get_exchange_secrets(self):
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT name, api_key, api_secret FROM user_credentials;'
        )
        result = result.fetchall()
        secret_data = {}
        for entry in result:
            if entry == 'rotkehlchen':
                continue
            name = entry[0]
            secret_data[name] = {
                'api_key': str(entry[1]),
                'api_secret': str(entry[2])
            }

        return secret_data

    def add_external_trade(
            self,
            time,
            location,
            pair,
            trade_type,
            amount,
            rate,
            fee,
            fee_currency,
            link,
            notes
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO trades('
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
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                time,
                location,
                pair,
                trade_type,
                amount,
                rate,
                fee,
                fee_currency,
                link,
                notes
            )
        )
        self.conn.commit()

    def edit_external_trade(
            self,
            trade_id,
            time,
            location,
            pair,
            trade_type,
            amount,
            rate,
            fee,
            fee_currency,
            link,
            notes
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO trades('
            '  id,'
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
            (
                trade_id,
                time,
                location,
                pair,
                trade_type,
                amount,
                rate,
                fee,
                fee_currency,
                link,
                notes
            )
        )
        self.conn.commit()

    def get_external_trades(self, from_ts=None, to_ts=None):
        cursor = self.conn.cursor()
        query = (
            'SELECT id,'
            '  time,'
            '  location,'
            '  pair,'
            '  type,'
            '  amount,'
            '  rate,'
            '  fee,'
            '  fee_currency,'
            '  link,'
            '  notes FROM trades WHERE location="external" '
        )
        bindings = ()
        if from_ts:
            query += 'AND time >= ? '
            bindings = (from_ts,)
            if to_ts:
                query += 'AND time <= ? '
                bindings = (from_ts, to_ts,)
        elif to_ts:
            query += 'AND time <= ? '
            bindings = (to_ts,)
        query += 'ORDER BY time ASC;'
        results = cursor.execute(query, bindings)
        results = results.fetchall()

        trades = []
        for result in results:
            trades.append({
                'id': result[0],
                'time': result[1],
                'location': result[2],
                'pair': result[3],
                'type': result[4],
                'amount': result[5],
                'rate': result[6],
                'fee': result[7],
                'fee_currency': result[8],
                'link': result[9],
                'notes': result[10],
            })

        return trades

    def delete_external_trade(self, trade_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM trades WHERE id=?', (trade_id,))
        self.conn.commit()

    def set_rotkehlchen_premium(self, api_key, api_secret):
        cursor = self.conn.cursor()
        # We don't care about previous value so this simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials(name, api_key, api_secret) VALUES (?, ?, ?)',
            ('rotkehlchen', api_key, api_secret)
        )
        self.conn.commit()
        # Do not update the last write here. If we are starting in a new machine
        # then this write is mandatory and to sync with data from server we need
        # an empty last write ts in that case
        # self.update_last_write()

    def get_rotkehlchen_premium(self):
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT api_key, api_secret FROM user_credentials where name="rotkehlchen";'
        )
        result = result.fetchall()
        if len(result) == 1:
            return result[0]
        else:
            return None
