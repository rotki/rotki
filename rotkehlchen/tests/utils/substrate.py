import logging
from typing import Optional, Sequence, Set, Tuple

import gevent
import requests
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException

from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.typing import (
    BlockNumber,
    DictNodeNameNodeAttributes,
    KusamaNodeName,
    NodeName,
    NodeNameAttributes,
    SubstrateChain,
)
from rotkehlchen.constants.assets import A_KSM
from rotkehlchen.fval import FVal

NODE_CONNECTION_TIMEOUT = 15

log = logging.getLogger(__name__)


# Accounts
SUBSTRATE_ACC1_PUBLIC_KEY = '0xa6659e4c3f22c2aa97d54a36e31ab57a617af62bd43ec62ed570771492069270'
SUBSTRATE_ACC1_DOT_ADDR = '14mB8stSf1vdP7WzbVr82YPgGGF7cBK9N7KxiVEac9UQgYj7'
SUBSTRATE_ACC1_KSM_ADDR = 'GLVeryFRbg5hEKvQZcAnLvXZEXhiYaBjzSDwrXBXrfPF7wj'
SUBSTRATE_ACC2_PUBLIC_KEY = '0x7e0bd3a5719525e3a4778010994c71be04eb6b7cd2e90931a76a3c89fa412b12'
SUBSTRATE_ACC2_DOT_ADDR = '13rGYiGMwLkHbt5Q5rcdyS4Tq7kmJgdE4d4tLex6Pwa7cVZA'
SUBSTRATE_ACC2_KSM_ADDR = 'FRb4hMAhvVjuztKtvNgjEbK863MR3tGSWB9a2EhKem6AygK'

# Use 2 nodes for tests
KUSAMA_TEST_NODES = (
    KusamaNodeName.PARITY,
    KusamaNodeName.ONFINALITY,
)

KUSAMA_SS58_FORMAT = 2
KUSAMA_TOKEN = A_KSM
KUSAMA_TOKEN_DECIMALS = FVal(12)
KUSAMA_DEFAULT_OWN_RPC_ENDPOINT = 'http://localhost:9933'


def attempt_connect_test_nodes(
        chain: SubstrateChain,
        timeout: int = NODE_CONNECTION_TIMEOUT,
        node_names: Optional[Sequence[NodeName]] = None,
) -> DictNodeNameNodeAttributes:
    """Attempt to connect to either a default sequence of reliable nodes for
    testing (e.g. Parity ones) or to a custom ones (via `node_names` param).
    Finally return the available node attributes map.

    NB: prioritising nodes by block_number is disabled.
    """
    def attempt_connect_node(node: NodeName) -> Tuple[NodeName, Optional[NodeNameAttributes]]:
        try:
            node_interface = SubstrateInterface(
                url=node.endpoint(),
                type_registry_preset=si_attributes.type_registry_preset,
                use_remote_preset=True,
            )
        except (requests.exceptions.RequestException, SubstrateRequestException) as e:
            message = (
                f'Substrate tests failed to connect to {node} node at '
                f'endpoint: {node.endpoint()}. Connection error: {str(e)}.',
            )
            log.error(message)
            return node, None

        log.info(f'Substrate tests connected to {node} node at endpoint: {node_interface.url}.')
        node_attributes = NodeNameAttributes(
            node_interface=node_interface,
            weight_block=BlockNumber(0),
        )
        return node, node_attributes

    if chain == SubstrateChain.KUSAMA:
        node_names = node_names or KUSAMA_TEST_NODES
        si_attributes = chain.substrate_interface_attributes()
    else:
        raise AssertionError(f'Unexpected substrate chain type: {chain}')

    greenlets = [gevent.spawn(attempt_connect_node, node) for node in node_names]
    jobs = gevent.joinall(greenlets, timeout=timeout)

    # Populate available node attributes map
    available_node_attributes_map: DictNodeNameNodeAttributes = {}
    for job in jobs:
        node, node_attributes = job.value
        if node_attributes:
            available_node_attributes_map[node] = node_attributes

    connected_nodes = set(available_node_attributes_map.keys())
    not_connected_nodes = set(node_names) - connected_nodes
    if not_connected_nodes:
        log.info(
            f'Substrate {chain} tests failed to connect to nodes: '
            f'{",".join([str(node) for node in not_connected_nodes])} ',
        )

    return available_node_attributes_map


def wait_until_all_substrate_nodes_connected(
        substrate_manager_connect_at_start: Sequence[NodeName],
        substrate_manager: SubstrateManager,
        timeout: int = NODE_CONNECTION_TIMEOUT,
) -> None:
    """Wait until all substrate nodes are connected or until a timeout is hit.
    """
    all_nodes: Set[NodeName] = set(substrate_manager_connect_at_start)
    connected: Set[NodeName] = set()
    try:
        with gevent.Timeout(timeout):
            while connected != all_nodes:
                for node in substrate_manager_connect_at_start:
                    if node in substrate_manager.available_node_attributes_map.keys():
                        connected.add(node)

                gevent.sleep(0.1)
    except gevent.Timeout:
        not_connected_nodes = all_nodes - connected
        log.info(
            f'{substrate_manager.chain} manager failed to connect to '
            f'nodes: {",".join([str(node) for node in not_connected_nodes])} '
            f'due to timeout of {NODE_CONNECTION_TIMEOUT}',
        )
