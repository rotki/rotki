import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v16->v17 upgrade')
def migrate_to_v17(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """This upgrade takes place in v1.44.0."""

    @progress_step('Drop the unused location_unsupported_assets table.')
    def _drop_location_unsupported_assets_table(write_cursor: DBCursor) -> None:
        """The exchange unsupported-asset blocklist was removed, so the table that backed
        it is no longer used. Drop it."""
        write_cursor.execute('DROP TABLE IF EXISTS location_unsupported_assets')

    @progress_step('Adding moralis to price_history_source_types')
    def _add_moralis_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('J', 10),
        )

    @progress_step('Create the rebasing tokens table.')
    def _create_rebasing_tokens_table(write_cursor: DBCursor) -> None:
        write_cursor.execute("""CREATE TABLE IF NOT EXISTS rebasing_tokens (
            asset_identifier TEXT NOT NULL PRIMARY KEY,
            FOREIGN KEY(asset_identifier) REFERENCES assets(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE
        );""")
        write_cursor.execute(
            'INSERT OR IGNORE INTO rebasing_tokens(asset_identifier) VALUES (?)',
            (A_STETH.identifier,),
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
