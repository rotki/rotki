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
    """Add Birdeye as a historical price source and key exchange asset mappings and binance
    pairs by connector identifier instead of a location character.

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

    @progress_step('Keying asset mappings and binance pairs by connector')
    def _rename_to_connectors(write_cursor: DBCursor) -> None:
        """The rows describe the symbol namespace of a connector, not where an event
        happened. The converted names are already the connector identifiers."""
        write_cursor.execute('DROP INDEX IF EXISTS idx_location_mappings_identifier')
        write_cursor.execute('ALTER TABLE location_asset_mappings RENAME TO connector_asset_mappings')  # noqa: E501
        write_cursor.execute('ALTER TABLE connector_asset_mappings RENAME COLUMN location TO connector')  # noqa: E501
        write_cursor.execute('CREATE INDEX IF NOT EXISTS idx_connector_mappings_identifier ON connector_asset_mappings (local_id)')  # noqa: E501
        write_cursor.execute('ALTER TABLE binance_pairs RENAME COLUMN location TO connector')

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=False,
    )
