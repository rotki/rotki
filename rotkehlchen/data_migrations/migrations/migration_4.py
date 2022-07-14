import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from rotkehlchen.constants.misc import ONE

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

DEFAULT_ETH_RPC = 'http://localhost:8545'


def read_and_write_nodes_in_database(write_cursor: 'DBCursor') -> None:
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / 'nodes.json', 'r') as f:
        nodes_info = json.loads(f.read())
        for node in nodes_info:
            write_cursor.execute(
                'INSERT OR IGNORE INTO web3_nodes(name, endpoint, owned, active, weight) VALUES (?, ?, ?, ?, ?);',  # noqa: E501
                (
                    node['name'],
                    node['endpoint'],
                    node['owned'],
                    node['active'],
                    str(FVal(node['weight'])),
                ),
            )


def copy_ethereum_rpc_endopoint(write_cursor: 'DBCursor') -> None:
    write_cursor.execute('SELECT value FROM settings WHERE name="eth_rpc_endpoint";')
    if (endpoint := write_cursor.fetchone()) is not None and endpoint[0] != DEFAULT_ETH_RPC:
        write_cursor.execute(
            'INSERT OR IGNORE INTO web3_nodes(name, endpoint, owned, active, weight) VALUES (?, ?, ?, ?, ?);',  # noqa: E501
            (
                "my node",
                endpoint[0],
                True,
                True,
                str(ONE),
            ),
        )
    write_cursor.execute('DELETE value FROM settings WHERE name="eth_rpc_endpoint"')


def data_migration_4(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    - Add ethereum nodes to connect to the database
    """
    read_and_write_nodes_in_database(write_cursor=write_cursor)
    # Connect to the nodes since the migration happens after the ethereum manager initialization
    nodes_to_connect = rotki.data.db.get_web3_nodes(only_active=True)
    rotki.chain_manager.ethereum.connect_to_multiple_nodes(nodes_to_connect)
    copy_ethereum_rpc_endopoint(write_cursor=write_cursor)
