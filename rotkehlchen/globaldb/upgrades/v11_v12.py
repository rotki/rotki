from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import CacheType
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v11->v12 upgrade')
def migrate_to_v12(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - Add new table for counterparty mappings

    - Clears Velodrome/Aerodrome pool and gauge cache entries to ensure a full refresh.
    Previously, fee and bribe addresses were not stored, so this forces an update
    to include them where available.

    - Reset Curve Lending vaults cache to force a repull.

    - Remove several Curve Lending caches which have been replaced with caches using the
    crvusd controller address as the second key part instead of the vault address.

    This upgrade takes place in v1.39.0"""
    @progress_step('Adding new tables.')
    def _create_new_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS counterparty_asset_mappings (
                counterparty TEXT NOT NULL,
                symbol TEXT NOT NULL,
                local_id TEXT NOT NULL COLLATE NOCASE,
                PRIMARY KEY (counterparty, symbol)
            );
            """,
        )

    @progress_step('Reset caches')
    def _reset_caches(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'DELETE FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_POOL_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_ADDRESS.serialize(),
                CacheType.AERODROME_POOL_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_ADDRESS.serialize(),
            ),
        )

        write_cursor.execute(
            'UPDATE unique_cache SET value=?, last_queried_ts = ? WHERE key = ?',
            ('0', 0, CacheType.CURVE_LENDING_VAULTS.serialize()),
        )

        write_cursor.executemany('DELETE FROM unique_cache WHERE key LIKE ? ESCAPE ?', [
            ('CURVE\\_LENDING\\_VAULT\\_AMM%', '\\'),
            ('CURVE\\_LENDING\\_VAULT\\_COLLATERAL\\_TOKEN%', '\\'),
        ])

    @progress_step(description='Deleting etherscan nodes')
    def _delete_etherscan_nodes(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'DELETE FROM default_rpc_nodes WHERE name IN (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                'etherscan',
                'optimism etherscan',
                'polygon pos etherscan',
                'arbitrum one etherscan',
                'base etherscan',
                'gnosis etherscan',
                'scroll etherscan',
                'bsc etherscan',
            ),
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
