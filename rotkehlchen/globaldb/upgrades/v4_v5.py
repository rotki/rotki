import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from rotkehlchen.constants.timing import ETH_PROTOCOLS_CACHE_REFRESH

from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_delete_general_cache_like,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values_at_ts,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import GeneralCacheType, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _create_new_tables(cursor: 'DBCursor') -> None:
    log.debug('Enter _create_new_tables')

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS default_rpc_nodes (
            identifier INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            weight TEXT NOT NULL,
            blockchain TEXT NOT NULL
        );
        """,
    )

    log.debug('Exit _create_new_tables')


def _populate_rpc_nodes(cursor: 'DBCursor', root_dir: Path) -> None:
    log.debug('Enter _populate_rpc_nodes')

    with open(root_dir / 'data' / 'nodes.json') as f:
        nodes_info = json.loads(f.read())

    nodes_tuples = [
        (node['name'], node['endpoint'], False, True, str(FVal(node['weight'])), node['blockchain'])  # noqa: E501
        for node in nodes_info
    ]
    log.debug(nodes_tuples)
    cursor.executemany(
        'INSERT INTO default_rpc_nodes(name, endpoint, owned, active, weight, blockchain) '  # noqa: E501
        'VALUES (?, ?, ?, ?, ?, ?)',
        nodes_tuples,
    )

    log.debug('Exit _populate_rpc_nodes')


def _reset_curve_cache(write_cursor: 'DBCursor') -> None:
    """Resets some parts of the curve cache.
    1. Resets last queried timestamp to query and save gauges.
    2. Clears curve pool tokens to requery them and save in the new format.
    """
    refreshing_timestamp = Timestamp(ts_now() - ETH_PROTOCOLS_CACHE_REFRESH - 1)
    lp_tokens = globaldb_get_general_cache_values(
        cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
    )
    if len(lp_tokens) == 0:
        log.error('Expected curve pools cache to be populated, but it was not')
        return

    globaldb_set_general_cache_values_at_ts(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_LP_TOKENS],
        values=lp_tokens,
        timestamp=refreshing_timestamp,
    )
    globaldb_delete_general_cache_like(
        write_cursor=write_cursor,
        key_parts=[GeneralCacheType.CURVE_POOL_TOKENS],
    )


def migrate_to_v5(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - Adds the `default_rpc_nodes` table.
    """
    log.debug('Entered globaldb v4->v5 upgrade')
    root_dir = Path(__file__).resolve().parent.parent.parent

    with connection.write_ctx() as cursor:
        _create_new_tables(cursor)
        _populate_rpc_nodes(cursor, root_dir)
        _reset_curve_cache(cursor)
