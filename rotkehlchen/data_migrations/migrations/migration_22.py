from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_22(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.40.2
    - Add auto_login_count and auto_login_confirmation_threshold settings.
    - Fix gnosispay_data table if it still has reversal_tx_hash column.
    """

    @progress_step(description='Fixing gnosispay_data table structure if needed')
    def _fix_gnosispay_table(rotki: 'Rotkehlchen') -> None:
        """Remove reversal_tx_hash column from gnosispay_data if it exists.
        This handles cases where the v49->v50 upgrade didn't run properly.
        """
        with rotki.data.db.conn.read_ctx() as cursor:
            # Check if the table exists and has the reversal_tx_hash column
            table_info = cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
            ).fetchone()
            
            if table_info and 'reversal_tx_hash' in table_info[0].lower():
                # Table has the old schema, need to fix it
                with rotki.data.db.user_write() as write_cursor:
                    write_cursor.execute("""
                    CREATE TABLE gnosispay_data_new (
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
                    INSERT INTO gnosispay_data_new
                    SELECT identifier, tx_hash, timestamp, merchant_name, merchant_city,
                        country, mcc, transaction_symbol, transaction_amount,
                        billing_symbol, billing_amount, reversal_symbol, reversal_amount
                    FROM gnosispay_data""")
                    write_cursor.execute('DROP TABLE gnosispay_data')
                    write_cursor.execute('ALTER TABLE gnosispay_data_new RENAME TO gnosispay_data')

    @progress_step(description='Adding auto-login security settings')
    def _add_auto_login_settings(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.user_write() as write_cursor:
            # Add auto_login_count setting with default value 0
            write_cursor.execute(
                'INSERT OR IGNORE INTO settings(name, value) VALUES(?, ?)',
                ('auto_login_count', '0'),
            )
            # Add auto_login_confirmation_threshold setting with default value 5
            write_cursor.execute(
                'INSERT OR IGNORE INTO settings(name, value) VALUES(?, ?)',
                ('auto_login_confirmation_threshold', '5'),
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
