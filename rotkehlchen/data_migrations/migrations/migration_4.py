import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

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
                'INSERT OR IGNORE INTO web3_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?);',  # noqa: E501
                (
                    node['name'],
                    node['endpoint'],
                    node['owned'],
                    node['active'],
                    str(FVal(node['weight'])),
                    node['blockchain'],
                ),
            )


def copy_ethereum_rpc_endpoint(write_cursor: 'DBCursor') -> None:
    write_cursor.execute('SELECT value FROM settings WHERE name="eth_rpc_endpoint";')
    if (endpoint := write_cursor.fetchone()) is not None and endpoint[0] != DEFAULT_ETH_RPC:
        write_cursor.execute(
            'INSERT OR IGNORE INTO web3_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?);',  # noqa: E501
            (
                "my node",
                endpoint[0],
                1,
                1,
                str(ONE),
                'ETH',
            ),
        )
    write_cursor.execute('DELETE FROM settings WHERE name="eth_rpc_endpoint"')


def data_migration_4(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    - Add ethereum nodes to connect to the database in 1.25
    """
    read_and_write_nodes_in_database(write_cursor=write_cursor)
    # Connect to the nodes since the migration happens after the ethereum manager initialization
    nodes_to_connect = rotki.data.db.get_web3_nodes(blockchain=SupportedBlockchain.ETHEREUM, only_active=True)  # noqa: E501
    rotki.chains_aggregator.ethereum.connect_to_multiple_nodes(nodes_to_connect)
    copy_ethereum_rpc_endpoint(write_cursor=write_cursor)
