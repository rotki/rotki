"""Test for data migration 22 - auto-login settings and gnosispay schema fix"""
from unittest.mock import patch

import pytest

from rotkehlchen.data_migrations.manager import MIGRATION_LIST, DataMigrationManager
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_adds_auto_login_settings(database: DBHandler) -> None:
    """Test that migration 22 adds auto_login_count and auto_login_confirmation_threshold"""
    rotki = MockRotkiForMigrations(database)

    # Verify settings don't exist before migration
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            "SELECT value FROM settings WHERE name='auto_login_count'"
        ).fetchone()
        assert result is None
        
        result = cursor.execute(
            "SELECT value FROM settings WHERE name='auto_login_confirmation_threshold'"
        ).fetchone()
        assert result is None

    # Run migration 22
    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[-1]]):
        DataMigrationManager(rotki).maybe_migrate_data()

    # Verify settings were added with correct default values
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            "SELECT value FROM settings WHERE name='auto_login_count'"
        ).fetchone()
        assert result is not None
        assert result[0] == '0'
        
        result = cursor.execute(
            "SELECT value FROM settings WHERE name='auto_login_confirmation_threshold'"
        ).fetchone()
        assert result is not None
        assert result[0] == '5'


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_fixes_gnosispay_schema(database: DBHandler) -> None:
    """Test that migration 22 fixes gnosispay_data table if it has old schema"""
    rotki = MockRotkiForMigrations(database)

    # Create gnosispay_data table with old schema (including reversal_tx_hash)
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
        
        # Add some test data
        write_cursor.execute("""
        INSERT INTO gnosispay_data (
            identifier, tx_hash, timestamp, merchant_name, country, mcc,
            transaction_symbol, transaction_amount
        ) VALUES (1, x'1234', 1000000, 'Test Merchant', 'US', 5411, 'USD', '10.50')
        """)

    # Verify table has old schema
    with database.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        assert 'reversal_tx_hash' in table_info[0].lower()

    # Run migration 22
    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[-1]]):
        DataMigrationManager(rotki).maybe_migrate_data()

    # Verify table schema was fixed (no more reversal_tx_hash)
    with database.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        assert 'reversal_tx_hash' not in table_info[0].lower()
        
        # Verify data was preserved
        result = cursor.execute(
            "SELECT identifier, merchant_name, transaction_amount FROM gnosispay_data WHERE identifier=1"
        ).fetchone()
        assert result is not None
        assert result[0] == 1
        assert result[1] == 'Test Merchant'
        assert result[2] == '10.50'


@pytest.mark.parametrize('data_migration_version', [21])
def test_migration_22_handles_missing_gnosispay_table(database: DBHandler) -> None:
    """Test that migration 22 doesn't fail if gnosispay_data table doesn't exist"""
    rotki = MockRotkiForMigrations(database)

    # Drop the table if it exists
    with database.user_write() as write_cursor:
        write_cursor.execute('DROP TABLE IF EXISTS gnosispay_data')

    # Run migration 22 - should not fail
    with patch('rotkehlchen.data_migrations.manager.MIGRATION_LIST', new=[MIGRATION_LIST[-1]]):
        DataMigrationManager(rotki).maybe_migrate_data()

    # Verify auto-login settings were still added
    with database.conn.read_ctx() as cursor:
        result = cursor.execute(
            "SELECT value FROM settings WHERE name='auto_login_count'"
        ).fetchone()
        assert result is not None
        assert result[0] == '0'
