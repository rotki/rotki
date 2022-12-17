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

DEAD_NODES_RPCS = [
    'https://api.mycryptoapi.com/eth',  # mycrypto
    'https://mainnet-nethermind.blockscout.com/',  # blockscout
    'https://mainnet.eth.cloud.ava.do/',  # avado
    'https://web3.1inch.exchange',  # 1inch
    'https://names.mewapi.io/rpc/eth',  # myetherwallet
]


def update_nodes_in_database(write_cursor: 'DBCursor') -> None:
    """
    Updates the ethereum nodes in the database. If nodes in the db are exactly the same as the
    defaults (i.e. the user has not customized them) then replace them with the new defaults.
    Else just delete the dead nodes and reweigh.
    """
    dir_path = Path(__file__).resolve().parent.parent.parent
    with open(dir_path / 'data' / 'nodes_as_of_1-26-1.json') as f:
        old_nodes_info = json.loads(f.read())
    with open(dir_path / 'data' / 'nodes.json') as f:
        new_nodes_info = json.loads(f.read())

    old_nodes = {
        (node['name'], node['endpoint'])
        for node in old_nodes_info
    }

    nodes_in_db = set(write_cursor.execute(
        'SELECT name, endpoint FROM rpc_nodes WHERE blockchain=? AND owned=0',
        (SupportedBlockchain.ETHEREUM.value,),
    ))

    if nodes_in_db == old_nodes:
        # If nodes in the db are exactly same as old defaults, replace them with new defaults
        log.debug('Completely replacing ethereum rpc nodes with new defaults')
        write_cursor.execute(
            'DELETE FROM rpc_nodes WHERE blockchain=? AND owned=0',
            (SupportedBlockchain.ETHEREUM.value,),
        )
        new_nodes_tuples = [
            (node['name'], node['endpoint'], False, True, str(FVal(node['weight'])), node['blockchain'])  # noqa: E501
            for node in new_nodes_info if node['blockchain'] == 'ETH'
        ]
        write_cursor.executemany(
            'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
            new_nodes_tuples,
        )
    else:
        # Else just delete dead nodes
        log.debug('Deleting dead ethereum rpc nodes but keeping the other ones')
        write_cursor.execute(
            f'DELETE FROM rpc_nodes WHERE endpoint IN ({",".join("?"*len(DEAD_NODES_RPCS))}) AND blockchain=?',  # noqa: E501
            [*DEAD_NODES_RPCS, SupportedBlockchain.ETHEREUM.value],
        )


def data_migration_6(write_cursor: 'DBCursor', rotki: 'Rotkehlchen') -> None:
    """
    - Update ethereum rpc nodes nodes in 1.26.2
    """
    log.debug('Enter data_migration_6')
    update_nodes_in_database(write_cursor=write_cursor)
    # Rebalance the nodes
    rotki.data.db.rebalance_rpc_nodes_weights(
        write_cursor=write_cursor,
        proportion_to_share=ONE,
        exclude_identifier=None,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    # Connect to the nodes since the migration happens after the ethereum manager initialization
    nodes_to_connect = rotki.data.db.get_rpc_nodes(blockchain=SupportedBlockchain.ETHEREUM, only_active=True)  # noqa: E501
    # when we sync a remote database the migrations are executed but the chain_manager
    # has not been created yet
    if hasattr(rotki, 'chain_manger') is True:
        rotki.chains_aggregator.ethereum.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)  # noqa: E501
    log.debug('Exit data_migration_6')
