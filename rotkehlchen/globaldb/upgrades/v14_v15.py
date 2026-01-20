import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v14->v15 upgrade')
def migrate_to_v15(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This upgrade takes place in v1.42.0"""

    @progress_step('Remove old cache keys.')
    def _remove_old_cache_keys(write_cursor: 'DBCursor') -> None:
        """Removes several cache keys that are no longer needed.
        - Aura pools - These pools are now loaded as needed during decoding and do not need to
           have a pool count stored in the cache.
        - Morpho vaults - This key is now a general cache key and stores addresses instead of just
           vault counts.
        - StakeDAO V2 vaults - Same as Morpho, this is now a general cache key storing addresses.
        - Beefy vaults - This key is now a general cache key and stores (address, boolean).
        - Pendle yield tokens - These tokens are now loaded as needed during decoding and do not
           need any cache entry.
        """
        write_cursor.executemany(
            'DELETE FROM unique_cache WHERE key LIKE ?',
            [
                ('AURA_POOLS%',),
                ('MORPHO_VAULTS%',),
                ('STAKEDAO_V2_VAULTS%',),
                ('BEEFY_VAULTS%',),
                ('PENDLE_YIELD_TOKENS%',),
            ],
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
