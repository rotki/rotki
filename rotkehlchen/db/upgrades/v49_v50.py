import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.schema import (
    DB_CREATE_SOLANA_ADDRESS_MAPPINGS,
    DB_CREATE_SOLANA_TRANSACTIONS,
    DB_CREATE_SOLANA_TX_ACCOUNT_KEYS,
    DB_CREATE_SOLANA_TX_INSTRUCTION_ACCOUNTS,
    DB_CREATE_SOLANA_TX_INSTRUCTIONS,
)
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
        write_cursor.executescript(
            f'{DB_CREATE_SOLANA_TRANSACTIONS} {DB_CREATE_SOLANA_TX_ACCOUNT_KEYS} {DB_CREATE_SOLANA_TX_INSTRUCTIONS} '  # noqa: E501
            f'{DB_CREATE_SOLANA_TX_INSTRUCTION_ACCOUNTS} {DB_CREATE_SOLANA_ADDRESS_MAPPINGS}',
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
