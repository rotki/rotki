import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.upgrades.upgrade_utils import process_solana_asset_migration
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v48->v49 upgrade')
def upgrade_v48_to_v49(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v48 to v49. This happened in v1.40 release.

    - Fix zksynclite_swaps table schema: change TEXT_NOT NULL to TEXT NOT NULL for to_amount column
    - Migrate solana assets to CAIPS format
    - Remove deprecated eth2_daily_staking_details table
    """
    @progress_step(description='Fixing zksynclite_swaps table schema.')
    def _fix_zksynclite_swaps_schema(write_cursor: 'DBCursor') -> None:
        # First check if the table exists
        if write_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'").fetchone() is None:  # noqa: E501
            log.debug('zksynclite_swaps table does not exist, skipping upgrade')
            return

        # Get the current schema to verify if we need to fix it
        schema_info = write_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='zksynclite_swaps'").fetchone()  # noqa: E501
        if schema_info and 'TEXT_NOT NULL' not in schema_info[0]:
            log.debug('zksynclite_swaps table does not have the TEXT_NOT NULL bug, skipping')
            return

        # Use update_table_schema to fix the table
        update_table_schema(
            write_cursor=write_cursor,
            table_name='zksynclite_swaps',
            schema="""tx_id INTEGER NOT NULL,
                from_asset TEXT NOT NULL,
                from_amount TEXT NOT NULL,
                to_asset TEXT NOT NULL,
                to_amount TEXT NOT NULL,
                FOREIGN KEY(tx_id) REFERENCES zksynclite_transactions(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
                FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE""",  # noqa: E501
            insert_columns='tx_id, from_asset, from_amount, to_asset, COALESCE(to_amount, "0")',
        )

    @progress_step(description='Migrating solana assets to CAIPS format.')
    def _migrate_solana_assets_to_caips(write_cursor: 'DBCursor') -> None:
        write_cursor.switch_foreign_keys('OFF')
        if len(process_solana_asset_migration(
            write_cursor=write_cursor,
            table_updates=[
                ('assets', 'identifier'),
                ('timed_balances', 'currency'),
                ('manually_tracked_balances', 'asset'),
                ('margin_positions', 'pl_currency'),
                ('margin_positions', 'fee_currency'),
                ('history_events', 'asset'),
            ],
        )) == 0:
            log.debug('Missing CSV file. Skipping solana assets migration.')
            return

        write_cursor.switch_foreign_keys('ON')
        # Delete the known duplicates
        write_cursor.execute('DELETE FROM assets WHERE identifier IN (?, ?)', ('TRISIG', 'HODLSOL'))  # noqa: E501

    @progress_step(description='Removing deprecated eth2_daily_staking_details table.')
    def _remove_eth2_daily_staking_details_table(write_cursor: 'DBCursor') -> None:
        """Remove the deprecated eth2_daily_staking_details table and its data"""
        write_cursor.execute('DROP TABLE IF EXISTS eth2_daily_staking_details;')

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except for the customized ones and those in zksync lite.
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

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=False)
