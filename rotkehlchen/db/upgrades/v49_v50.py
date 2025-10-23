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

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except for the customized ones and those in zksync lite.
        Notice that it happens first so changes in other tables don't affect this function.
        Code taken from previous upgrade
        """
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
            customized_events = write_cursor.execute(
                'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
                (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
            ).fetchone()[0]
            querystr = (
                "DELETE FROM history_events WHERE identifier IN ("
                "SELECT H.identifier from history_events H INNER JOIN evm_events_info E "
                "ON H.identifier=E.identifier AND E.tx_hash IN "
                "(SELECT tx_hash FROM evm_transactions) AND H.location != 'o')"  # location 'o' is zksync lite  # noqa: E501
            )
            bindings: tuple = ()
            if customized_events != 0:
                querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
                bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

            write_cursor.execute(querystr, bindings)
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
                (0,),  # decoded tx state
            )

    @progress_step(description='Add Crypto.com App event location labels.')
    def _add_cryptocom_location_labels(write_cursor: 'DBCursor') -> None:
        """Adds location labels for events imported via CSV from a Crypto.com App account."""
        write_cursor.execute(
            "UPDATE history_events SET location_label='Crypto.com App' WHERE "
            "location='P' AND location_label IS NULL AND identifier NOT IN "
            "(SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)",
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )

    @progress_step(description='Update accounting_rules table with is_event_specific column and constraint.')  # noqa: E501
    def _update_accounting_rules_table(write_cursor: 'DBCursor') -> None:
        """Does the following:
        - Add is_event_specific column to accounting_rules table
        - Create partial unique index for generic rules only
        """
        write_cursor.switch_foreign_keys('OFF')
        write_cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounting_rules_new(
            identifier INTEGER NOT NULL PRIMARY KEY,
            type TEXT NOT NULL,
            subtype TEXT NOT NULL,
            counterparty TEXT NOT NULL,
            taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),
            count_entire_amount_spend INTEGER NOT NULL CHECK (count_entire_amount_spend IN (0, 1)),
            count_cost_basis_pnl INTEGER NOT NULL CHECK (count_cost_basis_pnl IN (0, 1)),
            accounting_treatment TEXT,
            is_event_specific INTEGER NOT NULL CHECK (is_event_specific IN (0, 1)) DEFAULT 0
        );
        """)
        write_cursor.execute(
            'INSERT INTO accounting_rules_new(identifier, type, subtype, counterparty, taxable, '
            'count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment, is_event_specific) '  # noqa: E501
            'SELECT identifier, type, subtype, counterparty, taxable, '
            'count_entire_amount_spend, count_cost_basis_pnl, accounting_treatment, 0 '
            'FROM accounting_rules ORDER BY identifier',
        )
        write_cursor.execute('DROP TABLE accounting_rules')
        write_cursor.execute('ALTER TABLE accounting_rules_new RENAME TO accounting_rules')

        # Create partial unique index to maintain uniqueness for generic rules only
        write_cursor.execute("""
        CREATE UNIQUE INDEX unique_generic_accounting_rules
        ON accounting_rules(type, subtype, counterparty)
        WHERE is_event_specific = 0
        """)
        write_cursor.switch_foreign_keys('ON')

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
