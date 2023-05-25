
import logging
from typing import TYPE_CHECKING
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


DEFAULT_POLYGON_NODES_AT_V38 = [
    ('polygon etherscan', '', 0, 1, '0.25', 'POLYGON_POS'),
    ('ankr', 'https://rpc.ankr.com/polygon', 0, 1, '0.15', 'POLYGON_POS'),
    ('BlockPi', 'https://polygon.blockpi.network/v1/rpc/public', 0, 1, '0.15', 'POLYGON_POS'),
    ('PublicNode', 'https://polygon-bor.publicnode.com', 0, 1, '0.15', 'POLYGON_POS'),
    ('DefiLlama', 'https://polygon.llamarpc.com', 0, 1, '0.15', 'POLYGON_POS'),
    ('1rpc', 'https://1rpc.io/matic', 0, 1, '0.15', 'POLYGON_POS'),
]


def _add_polygon_pos_location(write_cursor: 'DBCursor') -> None:
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("h", 40);')


def _add_polygon_pos_nodes(write_cursor: 'DBCursor') -> None:
    write_cursor.executemany(
        'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        DEFAULT_POLYGON_NODES_AT_V38,
    )


def upgrade_v37_to_v38(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v37 to v38. This was in v1.29.0 release.

        - Add Polygon POS location
    """
    log.debug('Entered userdb v37->v38 upgrade')
    progress_handler.set_total_steps(2)
    with db.user_write() as write_cursor:
        _add_polygon_pos_location(write_cursor)
        progress_handler.new_step()
        _add_polygon_pos_nodes(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v37->v38 upgrade')
