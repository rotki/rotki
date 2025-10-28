"""Tests for auto-login database functionality"""
import pytest

from rotkehlchen.db.dbhandler import DBHandler


def test_auto_login_count_get_set(database: DBHandler):
    """Test getting and setting auto_login_count"""
    with database.conn.read_ctx() as cursor:
        # Should have default value of 0
        count = database.get_setting(cursor, 'auto_login_count')
        assert count == 0
    
    # Set to a new value
    with database.user_write() as write_cursor:
        database.set_setting(write_cursor, 'auto_login_count', 5)
    
    # Verify it was saved
    with database.conn.read_ctx() as cursor:
        count = database.get_setting(cursor, 'auto_login_count')
        assert count == 5
    
    # Reset to 0
    with database.user_write() as write_cursor:
        database.set_setting(write_cursor, 'auto_login_count', 0)
    
    # Verify reset
    with database.conn.read_ctx() as cursor:
        count = database.get_setting(cursor, 'auto_login_count')
        assert count == 0


def test_auto_login_confirmation_threshold_default(database: DBHandler):
    """Test that auto_login_confirmation_threshold has correct default value"""
    with database.conn.read_ctx() as cursor:
        threshold = database.get_setting(cursor, 'auto_login_confirmation_threshold')
        assert threshold == 5  # Default value


def test_auto_login_confirmation_threshold_get_set(database: DBHandler):
    """Test getting and setting auto_login_confirmation_threshold"""
    # Set to minimum value
    with database.user_write() as write_cursor:
        database.set_setting(write_cursor, 'auto_login_confirmation_threshold', 3)
    
    with database.conn.read_ctx() as cursor:
        threshold = database.get_setting(cursor, 'auto_login_confirmation_threshold')
        assert threshold == 3
    
    # Set to maximum value
    with database.user_write() as write_cursor:
        database.set_setting(write_cursor, 'auto_login_confirmation_threshold', 10)
    
    with database.conn.read_ctx() as cursor:
        threshold = database.get_setting(cursor, 'auto_login_confirmation_threshold')
        assert threshold == 10
    
    # Set to middle value
    with database.user_write() as write_cursor:
        database.set_setting(write_cursor, 'auto_login_confirmation_threshold', 7)
    
    with database.conn.read_ctx() as cursor:
        threshold = database.get_setting(cursor, 'auto_login_confirmation_threshold')
        assert threshold == 7


def test_gnosispay_schema_fix_method(database: DBHandler):
    """Test the _fix_gnosispay_schema_if_needed method"""
    # Create gnosispay_data with old schema
    with database.user_write() as write_cursor:
        write_cursor.execute('DROP TABLE IF EXISTS gnosispay_data')
        write_cursor.execute("""
        CREATE TABLE gnosispay_data (
            identifier INTEGER PRIMARY KEY NOT NULL,
            tx_hash BLOB NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL,
            merchant_name TEXT NOT NULL,
            merchant_city TEXT,
            country TEXT NOT NULL,
            mcc INTEGER NOT NULL,
            transaction_symbol TEXT NOT NULL,
            transaction_amount TEXT NOT NULL,
            billing_symbol TEXT,
            billing_amount TEXT,
            reversal_symbol TEXT,
            reversal_amount TEXT,
            reversal_tx_hash BLOB UNIQUE
        )""")
        
        # Add test data
        write_cursor.execute("""
        INSERT INTO gnosispay_data (
            identifier, tx_hash, timestamp, merchant_name, country, mcc,
            transaction_symbol, transaction_amount
        ) VALUES (1, x'abcd', 1000000, 'Test Store', 'DE', 5411, 'EUR', '25.99')
        """)
    
    # Verify old schema
    with database.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        assert 'reversal_tx_hash' in table_info[0].lower()
    
    # Run the fix method
    database._fix_gnosispay_schema_if_needed()
    
    # Verify new schema (no reversal_tx_hash)
    with database.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        assert 'reversal_tx_hash' not in table_info[0].lower()
        
        # Verify data was preserved
        result = cursor.execute(
            "SELECT identifier, merchant_name, transaction_amount FROM gnosispay_data WHERE identifier=1"
        ).fetchone()
        assert result[0] == 1
        assert result[1] == 'Test Store'
        assert result[2] == '25.99'


def test_gnosispay_schema_fix_with_correct_schema(database: DBHandler):
    """Test that _fix_gnosispay_schema_if_needed doesn't break correct schema"""
    # Create gnosispay_data with correct schema (no reversal_tx_hash)
    with database.user_write() as write_cursor:
        write_cursor.execute('DROP TABLE IF EXISTS gnosispay_data')
        write_cursor.execute("""
        CREATE TABLE gnosispay_data (
            identifier INTEGER PRIMARY KEY NOT NULL,
            tx_hash BLOB NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL,
            merchant_name TEXT NOT NULL,
            merchant_city TEXT,
            country TEXT NOT NULL,
            mcc INTEGER NOT NULL,
            transaction_symbol TEXT NOT NULL,
            transaction_amount TEXT NOT NULL,
            billing_symbol TEXT,
            billing_amount TEXT,
            reversal_symbol TEXT,
            reversal_amount TEXT
        )""")
        
        write_cursor.execute("""
        INSERT INTO gnosispay_data (
            identifier, tx_hash, timestamp, merchant_name, country, mcc,
            transaction_symbol, transaction_amount
        ) VALUES (1, x'1234', 1000000, 'Correct Schema Store', 'FR', 5812, 'EUR', '15.50')
        """)
    
    # Run the fix method - should do nothing
    database._fix_gnosispay_schema_if_needed()
    
    # Verify schema is still correct
    with database.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        assert 'reversal_tx_hash' not in table_info[0].lower()
        
        # Verify data is intact
        result = cursor.execute(
            "SELECT identifier, merchant_name FROM gnosispay_data WHERE identifier=1"
        ).fetchone()
        assert result[0] == 1
        assert result[1] == 'Correct Schema Store'


def test_gnosispay_schema_fix_without_table(database: DBHandler):
    """Test that _fix_gnosispay_schema_if_needed handles missing table gracefully"""
    # Drop table if it exists
    with database.user_write() as write_cursor:
        write_cursor.execute('DROP TABLE IF EXISTS gnosispay_data')
    
    # Run the fix method - should not fail
    database._fix_gnosispay_schema_if_needed()
    
    # Verify nothing broke
    with database.conn.read_ctx() as cursor:
        # Check that we can still query other tables
        result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'").fetchone()
        assert result is not None
