import logging
from typing import TYPE_CHECKING

from rotkehlchen.constants.misc import ONE
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _maybe_add_llamanode(write_cursor: 'DBCursor') -> None:
    """
    Add LlamaNode to the list of ethereum web3 nodes if it isn't already present.
    """
    nodes_in_db = set(write_cursor.execute(
        'SELECT endpoint FROM rpc_nodes WHERE blockchain=? AND owned=0',
        (SupportedBlockchain.ETHEREUM.value,),
    ))

    llama_rpc = 'https://eth.llamarpc.com'
    if llama_rpc in nodes_in_db:
        return

    write_cursor.execute(
        'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
        ('LlamaNodes', llama_rpc, False, True, '0.25', SupportedBlockchain.ETHEREUM.value),
    )


def data_migration_7(rotki: 'Rotkehlchen') -> None:
    """
    - Add llamanode to the web3 nodes in 1.26.3
    """
    log.debug('Enter data_migration_7')
    with rotki.data.db.user_write() as write_cursor:
        _maybe_add_llamanode(write_cursor=write_cursor)
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
    if (chains_aggregator := getattr(rotki, 'chains_aggregator', None)) is not None:
        chains_aggregator.ethereum.node_inquirer.connect_to_multiple_nodes(nodes_to_connect)
    log.debug('Exit data_migration_7')
