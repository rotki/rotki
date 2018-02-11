import time
import os
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkelchen.fval import FVal
from rotkelchen.errors import InputError


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types
class DBHandler(object):

    def __init__(self, database_directory, username, password):
        self.conn = sqlcipher.connect(os.path.join(database_directory, 'rotkehlchen.db'))
        self.conn.text_factory = str
        try:
            self.conn.executescript('PRAGMA key="{}"; pragma kdf_iter=64000;'.format(password))
        except sqlcipher.DatabaseError:
            raise InputError('Wrong password while decrypting the database')

        self.conn.execute('PRAGMA foreign_keys=ON')
        cursor = self.conn.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS timed_balances ('
            '    time INTEGER, currency VARCHAR[12], amount DECIMAL, usd_value DECIMAL'
            ')'
        )
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
        self.conn.commit()

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

    def add_timed_unique_data(self, time, net_usd):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO timed_unique_data(time, net_usd) VALUES (?, ?)',
            (time, net_usd)
        )
        self.conn.commit()

    def remove(self):
        cursor = self.conn.cursos()
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
