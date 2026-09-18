import logging
from typing import TYPE_CHECKING

from rotkehlchen.locations.legacy_chars import V53_CHAR_TO_NAME
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v18->v19 upgrade')
def migrate_to_v19(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """Add Birdeye as a historical price source and store the locations of exchange asset
    mappings and binance pairs as text identifiers instead of one character.

    This upgrade takes place in v1.45
    """

    @progress_step('Adding Birdeye to price_history_source_types')
    def _add_birdeye_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('L', 12),
        )

    @progress_step('Storing exchange locations as text identifiers')
    def _convert_location_characters(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'CREATE TEMP TABLE location_char_mapping (old TEXT PRIMARY KEY, new TEXT NOT NULL)',
        )
        write_cursor.executemany(
            'INSERT INTO location_char_mapping(old, new) VALUES (?, ?)',
            list(V53_CHAR_TO_NAME.items()),
        )
        for table in ('location_asset_mappings', 'binance_pairs'):
            if (unknown := write_cursor.execute(
                f'DELETE FROM {table} WHERE location IS NOT NULL AND location NOT IN '
                '(SELECT old FROM location_char_mapping)',
            ).rowcount) != 0:
                log.warning('Removed %s %s rows with an unknown location', unknown, table)
            write_cursor.execute(
                f'UPDATE {table} SET location=(SELECT new FROM location_char_mapping '
                f'WHERE old={table}.location) WHERE location IS NOT NULL',
            )
        write_cursor.execute('DROP TABLE location_char_mapping')

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=False,
    )
