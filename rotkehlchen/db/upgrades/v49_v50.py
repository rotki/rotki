import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v49->v50 upgrade')
def upgrade_v49_to_v50(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v49 to v50. This happened in the v1.41 release."""

    @progress_step(description='Add Crypto.com App event location labels.')
    def _add_cryptocom_location_labels(write_cursor: 'DBCursor') -> None:
        """Adds location labels for events imported via CSV from a Crypto.com App account."""
        write_cursor.execute(
            "UPDATE history_events SET location_label='Crypto.com App' WHERE "
            "location='P' AND location_label IS NULL AND identifier NOT IN "
            "(SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)",
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )

    @progress_step(description='Create table for linking accounting rules to specific events.')
    def _create_accounting_rule_events_table(write_cursor: 'DBCursor') -> None:
        """Create a table to link accounting rules to specific events."""
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_rule_events(
            identifier INTEGER NOT NULL PRIMARY KEY,
            rule_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            FOREIGN KEY(event_id) REFERENCES history_events(identifier) ON DELETE CASCADE,
            FOREIGN KEY(rule_id) REFERENCES accounting_rules(identifier) ON DELETE CASCADE,
            UNIQUE(rule_id, event_id)
        );
        """)

    @progress_step(description='Swap SOL-2 to SOL asset identifier.')
    def _swap_sol2_to_sol(write_cursor: 'DBCursor') -> None:
        """Swap SOL-2 to SOL throughout the user database."""
        write_cursor.execute(
            'UPDATE assets SET identifier = ? WHERE identifier = ?',
            ('SOL', 'SOL-2'),
        )

    @progress_step(description='Add solana transaction tables')
    def _add_solana_transaction_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS solana_transactions (
                identifier INTEGER PRIMARY KEY NOT NULL,
                slot INTEGER NOT NULL,
                fee INTEGER NOT NULL,
                block_time INTEGER NOT NULL,
                success INTEGER NOT NULL CHECK(success IN (0, 1)),
                signature BLOB NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS solana_tx_account_keys (
                tx_id INTEGER NOT NULL,
                account_index INTEGER NOT NULL,
                address BLOB NOT NULL,
                PRIMARY KEY(tx_id, account_index),
                FOREIGN KEY(tx_id) REFERENCES solana_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
            );
            CREATE TABLE IF NOT EXISTS solana_tx_instructions (
                identifier INTEGER NOT NULL PRIMARY KEY,
                tx_id INTEGER NOT NULL,
                execution_index INTEGER NOT NULL,
                parent_execution_index INTEGER NOT NULL,
                program_id_index INTEGER NOT NULL,
                data BLOB,
                FOREIGN KEY(tx_id) REFERENCES solana_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(tx_id, program_id_index) REFERENCES solana_tx_account_keys(tx_id, account_index) ON DELETE CASCADE ON UPDATE CASCADE
            );
            CREATE TABLE IF NOT EXISTS solana_tx_instruction_accounts (
                identifier INTEGER NOT NULL PRIMARY KEY,
                instruction_id INTEGER NOT NULL,
                account_order INTEGER NOT NULL,
                account_index INTEGER NOT NULL,
                tx_id INTEGER NOT NULL,
                FOREIGN KEY(instruction_id) REFERENCES solana_tx_instructions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(tx_id, account_index) REFERENCES solana_tx_account_keys(tx_id, account_index) ON DELETE CASCADE ON UPDATE CASCADE
            );
            CREATE TABLE IF NOT EXISTS solanatx_address_mappings (
                tx_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                PRIMARY KEY(tx_id, address),
                FOREIGN KEY(tx_id) REFERENCES solana_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
            );
            CREATE TABLE IF NOT EXISTS solana_tx_mappings (
                tx_id INTEGER NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY(tx_id) references solana_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
                PRIMARY KEY (tx_id, value)
            );
        """)  # noqa: E501

    @progress_step(description='Refactor EVM events metadata table into chain agnostic table.')
    def _refactor_evm_events_info_table(write_cursor: 'DBCursor') -> None:
        write_cursor.switch_foreign_keys('OFF')
        write_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS chain_events_info (
                identifier INTEGER PRIMARY KEY,
                tx_ref BLOB NOT NULL,
                counterparty TEXT,
                address TEXT,
                FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
            );
        """)  # noqa: E501
        write_cursor.execute(
            'INSERT INTO chain_events_info(identifier, tx_ref, counterparty, address) '
            'SELECT identifier, tx_hash, counterparty, address FROM evm_events_info',
        )
        write_cursor.switch_foreign_keys('ON')
        write_cursor.execute('DROP TABLE evm_events_info')

    @progress_step(description='Remove monerium credentials.')
    def _remove_monerium(write_cursor: 'DBCursor') -> None:
        """
        Since monerium authentication, switches to oauth we should delete user's
        monerium credentials from the DB
        """
        write_cursor.execute(
            'DELETE FROM external_service_credentials WHERE name = ?',
            ('monerium',),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
