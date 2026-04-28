import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.prices import (
    BITCOIN_GENESIS_BLOCK_TS,
    CRYPTOCOMPARE_INVALID_PRICE_TS_CUTOFF,
)
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v15->v16 upgrade')
def migrate_to_v16(
        connection: 'DBConnection',
        progress_handler: 'DBUpgradeProgressHandler',
) -> None:
    """This upgrade takes place in v1.43.0."""

    @progress_step('Create price history timestamp order index.')
    def _create_price_history_timestamp_order_index(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_desc_order '
            'ON price_history (timestamp DESC, from_asset, to_asset, source_type);',
        )

    @progress_step('Remove invalid old Cryptocompare prices.')
    def _remove_invalid_old_cryptocompare_prices(write_cursor: 'DBCursor') -> None:
        """
        With the introduction of the new price handling we identified some incorrect
        entries in the price cache coming from Cryptocompare. We checked that these
        entries are old, dating back to at least 2024, and they have not reappeared
        since.

        Since rotki accepted any timestamp returned by Cryptocompare, the most likely
        source is invalid price data from the hourly candle endpoint used by the
        background cache task.

        This step uses an old enough arbitrary cutoff date to find affected assets, then
        removes Cryptocompare prices older than the asset start timestamp. If an asset has
        no start timestamp, the Bitcoin genesis block timestamp is used as the crypto
        price floor.
        """
        cryptocompare_source = HistoricalPriceOracle.CRYPTOCOMPARE.serialize_for_db()
        deleted_rows = 0
        affected_assets = write_cursor.execute(
            'SELECT DISTINCT P.from_asset, C.started FROM price_history AS P '
            'LEFT JOIN common_asset_details AS C ON C.identifier=P.from_asset '
            'WHERE P.source_type=? AND P.timestamp<?',
            (cryptocompare_source, CRYPTOCOMPARE_INVALID_PRICE_TS_CUTOFF),
        ).fetchall()
        if len(affected_assets) != 0:
            write_cursor.executemany(
                'DELETE FROM price_history WHERE source_type=? AND from_asset=? AND timestamp<?',
                [
                    (
                        cryptocompare_source,
                        asset_id,
                        started if started is not None else BITCOIN_GENESIS_BLOCK_TS,
                    ) for asset_id, started in affected_assets
                ],
            )
            deleted_rows = write_cursor.rowcount

        log.info(f'Removed {deleted_rows} invalid old Cryptocompare price entries.')

    perform_globaldb_upgrade_steps(connection, progress_handler)
