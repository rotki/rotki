
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


def _reduce_internal_txs(write_cursor: 'DBCursor') -> None:
    """Reduce the size of the evm internal transactions table by removing unused columns"""
    log.debug('Enter _reduce_internal_txs')
    table_exists = write_cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master '
        'WHERE type="table" AND name="evm_internal_transactions"',
    ).fetchone()[0] == 1
    table_to_create = 'evm_internal_transactions'
    if table_exists is True:
        table_to_create += '_new'
    write_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_to_create} (
        parent_tx_hash BLOB NOT NULL,
        chain_id INTEGER NOT NULL,
        trace_id INTEGER NOT NULL,
        from_address TEXT NOT NULL,
        to_address TEXT,
        value TEXT NOT NULL,
        FOREIGN KEY(parent_tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)
    );""")  # noqa: E501
    if table_exists is True:
        write_cursor.execute(
            'INSERT INTO evm_internal_transactions_new SELECT parent_tx_hash, chain_id, trace_id, '
            'from_address, to_address, value FROM evm_internal_transactions',
        )
        write_cursor.execute('DROP TABLE evm_internal_transactions')
        write_cursor.execute(
            'ALTER TABLE evm_internal_transactions_new RENAME TO evm_internal_transactions',
        )
    log.debug('Exit _reduce_internal_txs')


def upgrade_v37_to_v38(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v37 to v38. This was in v1.29.0 release.

        - Add Polygon POS location
    """
    log.debug('Entered userdb v37->v38 upgrade')
    progress_handler.set_total_steps(3)
    with db.user_write() as write_cursor:
        _reduce_internal_txs(write_cursor)
        progress_handler.new_step()
        _add_polygon_pos_location(write_cursor)
        progress_handler.new_step()
        _add_polygon_pos_nodes(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v37->v38 upgrade')
