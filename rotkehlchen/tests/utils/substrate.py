import logging
from collections.abc import Sequence

import requests
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException

from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.types import (
    BlockNumber,
    DictNodeNameNodeAttributes,
    KusamaNodeName,
    NodeName,
    NodeNameAttributes,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.gevent_compat import Timeout, joinall, sleep, spawn

NODE_CONNECTION_TIMEOUT = 15

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
POLKADOT_SS58_FORMAT = 2
KUSAMA_MAIN_ASSET_DECIMALS = FVal(12)
KUSAMA_DEFAULT_OWN_RPC_ENDPOINT = 'http://localhost:9933'
KUSAMA_TEST_RPC_ENDPOINT = 'https://ksm.getblock.io/ae78eb1d-2643-4e22-b691-0ecb9d9c5e08/mainnet/'  # made by lef for testing # noqa: E501


def attempt_connect_test_nodes(
        chain: SupportedBlockchain,
        timeout: int = NODE_CONNECTION_TIMEOUT,
        node_names: Sequence[NodeName] | None = None,
) -> DictNodeNameNodeAttributes:
    """Attempt to connect to either a default sequence of reliable nodes for
    testing (e.g. Parity ones) or to a custom ones (via `node_names` param).
    Finally return the available node attributes map.

    NB: prioritising nodes by block_number is disabled.
    """
    def attempt_connect_node(node: NodeName) -> tuple[NodeName, NodeNameAttributes | None]:
        try:
            node_interface = SubstrateInterface(
                url=node.endpoint(),
                type_registry_preset='kusama',
                use_remote_preset=True,
            )
        except (requests.exceptions.RequestException, SubstrateRequestException) as e:
            message = (
                f'Substrate tests failed to connect to {node} node at '
                f'endpoint: {node.endpoint()}. Connection error: {e!s}.',
            )
            log.error(message)
            return node, None

        log.info(f'Substrate tests connected to {node} node at endpoint: {node_interface.url}.')
        node_attributes = NodeNameAttributes(
            node_interface=node_interface,
            weight_block=BlockNumber(0),
        )
        return node, node_attributes

    if chain == SupportedBlockchain.KUSAMA:
        node_names = node_names or KUSAMA_TEST_NODES
    else:
        raise AssertionError(f'Unexpected substrate chain type: {chain} at test')

    greenlets = [spawn(attempt_connect_node, node) for node in node_names]
    jobs = joinall(greenlets, timeout=timeout)

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
    """Wait until all substrate nodes are connected or until a timeout is hit"""
    all_nodes: set[NodeName] = set(substrate_manager_connect_at_start)
    connected: set[NodeName] = set()
    try:
        with Timeout(timeout):
            while connected != all_nodes:
                for node in substrate_manager_connect_at_start:
                    if node in substrate_manager.available_node_attributes_map:
                        connected.add(node)

                sleep(0.1)
    except Timeout:
        not_connected_nodes = all_nodes - connected
        log.info(
            f'{substrate_manager.chain} manager failed to connect to '
            f'nodes: {",".join([str(node) for node in not_connected_nodes])} '
            f'due to timeout of {NODE_CONNECTION_TIMEOUT}',
        )
