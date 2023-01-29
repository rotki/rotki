import json
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def populate_rpc_nodes_in_database(write_cursor: 'DBCursor') -> None:
    """Populates the rpc nodes in the datatabase from nodes.json

    This is supposed to run for a clean new DB
    """
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / 'nodes.json') as f:
        nodes_info = json.loads(f.read())

    nodes_tuples = [
        (node['name'], node['endpoint'], False, True, str(FVal(node['weight'])), node['blockchain'])  # noqa: E501
        for node in nodes_info
    ]
    write_cursor.executemany(
        'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
        nodes_tuples,
    )
