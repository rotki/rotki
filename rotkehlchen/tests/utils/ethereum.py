import logging
import os
from typing import List, Tuple

import gevent

from rotkehlchen.chain.ethereum.manager import NodeName

NODE_CONNECTION_TIMEOUT = 10

log = logging.getLogger(__name__)

INFURA_TEST = 'https://mainnet.infura.io/v3/66302b8fb9874614905a3cbe903a0dbb'

ETHEREUM_TEST_PARAMETERS: Tuple[str, List[Tuple]]
if 'GITHUB_WORKFLOW' in os.environ:
    # For Github actions don't use infura. It seems that connecting to it
    # from Github actions hangs and times out
    ETHEREUM_TEST_PARAMETERS = ('ethrpc_endpoint,ethereum_manager_connect_at_start, call_order', [
        # Query etherscan only
        ('', (), (NodeName.ETHERSCAN,)),
    ])
else:
    # For Travis and local tests also use Infura, works fine
    ETHEREUM_TEST_PARAMETERS = ('ethrpc_endpoint,ethereum_manager_connect_at_start, call_order', [
        # Query etherscan only
        ('', (), (NodeName.ETHERSCAN,)),
        # For "our own" node querying use infura
        (
            INFURA_TEST,
            (NodeName.OWN,),
            (NodeName.OWN,),
        ),
    ])


def wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start,
        ethereum,
        timeout: int = NODE_CONNECTION_TIMEOUT,
):
    """Wait until all ethereum nodes are connected or until a timeout is hit"""
    connected = [False] * len(ethereum_manager_connect_at_start)
    try:
        with gevent.Timeout(timeout):
            while not all(connected):
                for idx, node_name in enumerate(ethereum_manager_connect_at_start):
                    if node_name in ethereum.web3_mapping:
                        connected[idx] = True

                gevent.sleep(0.1)
    except gevent.Timeout:
        names = [
            str(x) for idx, x in enumerate(ethereum_manager_connect_at_start) if not connected[idx]
        ]
        log.info(
            f'Did not connect to nodes: {",".join(names)} due to '
            f'timeout of {NODE_CONNECTION_TIMEOUT}',
        )
