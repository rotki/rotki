import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
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

    @progress_step('Add asset flags table.')
    def _add_asset_flags_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            """CREATE TABLE IF NOT EXISTS asset_flags(
                identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
                flag TEXT NOT NULL,
                FOREIGN KEY(identifier) REFERENCES assets(identifier)
                    ON UPDATE CASCADE ON DELETE CASCADE
            );""",
        )

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

    @progress_step('Normalize underlying token weights.')
    def _normalize_underlying_token_weights(write_cursor: 'DBCursor') -> None:
        """Normalizes underlying token weights so they sum to exactly 1.

        Balancer pools (v2 and v3) have weights that don't sum to exactly 1 due to bad
        source data from the API. 812 pools affected. This fixes them by adjusting the
        last weight to absorb the difference: last_weight = 1 - sum(other_weights).
        """
        write_cursor.execute(
            'SELECT parent_token_entry, identifier, weight '
            'FROM underlying_tokens_list '
            'WHERE parent_token_entry IN ('
            '    SELECT parent_token_entry FROM underlying_tokens_list '
            '    GROUP BY parent_token_entry '
            '    HAVING ABS(SUM(CAST(weight AS REAL)) - 1.0) > 1e-16'
            ') ORDER BY parent_token_entry, identifier',
        )
        tokens_to_fix: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
        for parent, identifier, weight in write_cursor:
            tokens_to_fix[parent].append((identifier, weight))

        updates: list[tuple[str, str, str]] = []
        for parent_token_entry, tokens in tokens_to_fix.items():
            weight_sum = ZERO
            for idx, (identifier, weight_str) in enumerate(tokens):
                if idx == len(tokens) - 1:
                    updates.append((str(ONE - weight_sum), identifier, parent_token_entry))
                else:
                    weight_sum += FVal(weight_str)

        write_cursor.executemany(
            'UPDATE underlying_tokens_list SET weight = ? '
            'WHERE identifier = ? AND parent_token_entry = ?',
            updates,
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
