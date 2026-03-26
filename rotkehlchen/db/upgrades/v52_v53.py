import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v52->v53 upgrade')
def upgrade_v52_to_v53(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v52 to v53 by adding Hyperliquid location and RPC nodes."""

    @progress_step(description='Adding Hyperliquid location to the DB.')
    def _add_hyperliquid_location(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Hyperliquid */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('y', 57);
        """)

    @progress_step(description='Adding Hyperliquid RPC nodes.')
    def _add_hyperliquid_rpc_nodes(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            ('hyperliquid', 'https://rpc.hyperliquid.xyz/evm', False, True, '0.40', 'HYPERLIQUID'),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                'hyperliquid drpc',
                'https://hyperliquid.drpc.org',
                False,
                True,
                '0.30',
                'HYPERLIQUID',
            ),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (
                'hyperliquid onfinality',
                'https://hyperliquid.api.onfinality.io/evm/public',
                False,
                True,
                '0.20',
                'HYPERLIQUID',
            ),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
