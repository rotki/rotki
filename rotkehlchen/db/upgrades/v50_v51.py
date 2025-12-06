import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v50->v51 upgrade')
def upgrade_v50_to_v51(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v50 to v51. This happened in the v1.42 release."""

    @progress_step(description='Rename event_identifier column to group_identifier in history_events table.')  # noqa: E501
    def _rename_event_identifier_to_group_identifier(write_cursor: 'DBCursor') -> None:
        """Rename event_identifier column to group_identifier in history_events table."""
        write_cursor.switch_foreign_keys('OFF')
        update_table_schema(
            write_cursor=write_cursor,
            table_name='history_events',
            schema="""identifier INTEGER NOT NULL PRIMARY KEY,
            entry_type INTEGER NOT NULL,
            group_identifier TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            location_label TEXT,
            asset TEXT NOT NULL,
            amount TEXT NOT NULL,
            notes TEXT,
            type TEXT NOT NULL,
            subtype TEXT NOT NULL,
            extra_data TEXT,
            ignored INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            UNIQUE(group_identifier, sequence_index)""",
            insert_columns='identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored',  # noqa: E501
            insert_order='(identifier, entry_type, group_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored)',  # noqa: E501
        )
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Create Lido CSM support tables.')
    def _create_lido_csm_tables(write_cursor: 'DBCursor') -> None:
        """Create Lido CSM specific tables."""
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS lido_csm_node_operators (
            node_operator_id INTEGER NOT NULL PRIMARY KEY,
            address TEXT NOT NULL,
            blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
            FOREIGN KEY(blockchain, address)
                REFERENCES blockchain_accounts(blockchain, account)
                ON DELETE CASCADE
        );
        """)
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS lido_csm_node_operator_metrics (
            node_operator_id INTEGER NOT NULL PRIMARY KEY,
            operator_type_id INTEGER,
            bond_current TEXT,
            bond_required TEXT,
            bond_claimable TEXT,
            total_deposited_validators INTEGER,
            rewards_pending TEXT,
            updated_ts INTEGER,
            FOREIGN KEY(node_operator_id)
                REFERENCES lido_csm_node_operators(node_operator_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)

    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Kraken Futures */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('x', 56);
        """)

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
