import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def read_and_write_nodes_in_database(write_cursor: 'DBCursor') -> None:
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / 'nodes.json', 'r') as f:
        nodes_info = json.loads(f.read())
        for node in nodes_info:
            write_cursor.execute(
                'INSERT OR IGNORE INTO web3_nodes(name, address, owned, active, weight) VALUES (?, ?, ?, ?, ?);',  # noqa: E501
                (
                    node['node'],
                    node['endpoint'],
                    node['owned'],
                    node['active'],
                    str(FVal(node['weight'])),
                ),
            )


def data_migration_4(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    - Add ethereum nodes to connect to the database
    """
    read_and_write_nodes_in_database(write_cursor=write_cursor)
    # Connect to the nodes since the migration happens after the ethereum manager initialization
    nodes_to_connect = rotki.data.db.get_web3_nodes(only_active=True)
    rotki.chain_manager.ethereum.connect_to_multiple_nodes(nodes_to_connect)
