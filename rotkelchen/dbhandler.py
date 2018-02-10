import os
import sqlite3


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types
class DBHandler(object):

    def __init__(self, database_directory):
        self.conn = sqlite3.connect(os.path.join(database_directory, 'rotkehlchen.db'))
        self.conn.text_factory = str
        self.conn.execute('PRAGMA foreign_keys=ON')
        cursor = self.conn.cursor()

        # temporary for testing
        cursor.execute('DROP TABLE IF EXISTS timed_balances')
        cursor.execute('DROP TABLE IF EXISTS timed_location_data')
        cursor.execute('DROP TABLE IF EXISTS timed_unique_data')

        cursor.execute(
            'CREATE TABLE IF NOT EXISTS timed_balances ('
            '    time INTEGER, currency VARCHAR[12], amount DECIMAL, usd_value DECIMAL, net_percentage DECIMAL'
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS timed_location_data ('
            '    time INTEGER, location VARCHAR[24], usd_value DECIMAL, net_percentage DECIMAL'
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
        (time, asset, amount, usd_value, perc)"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT INTO timed_balances('
            '    time, currency, amount, usd_value, net_percentage) '
            ' VALUES(?, ?, ?, ?, ?)',
            balances
        )
        self.conn.commit()

    def add_multiple_location_data(self, location_data):
        """Execute addition of multiple location data in the DB

        location_data should be a list of tuples each containing:
        (time, location, usd_value, perc)"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT INTO timed_location_data('
            '    time, location, usd_value, net_percentage) '
            ' VALUES(?, ?, ?, ?)',
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
