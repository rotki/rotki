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
SUBSTRATE_ACC3_PUBLIC_KEY = '0x1c86776eda34405584e710a7363650afd1f2b38ef72836317b11ef1303a0ae72'
SUBSTRATE_ACC3_DOT_ADDR = '1eQHa1sa4ZuHy9YPagUfV2EB5kmAeCqUtasDfz1kSJzHC4R'
SUBSTRATE_ACC3_KSM_ADDR = 'DDioZ6gLeKMc5xUCeSXRHZ5U43MH1Tsrmh8T3Gcg9Vxr6DY'
SUBSTRATE_ACC4_PUBLIC_KEY = '0x487ee7e677203b4209af2ffaec0f5068033c870c97fee18b31b4aee524089943'
SUBSTRATE_ACC4_DOT_ADDR = '12e49WD6bi75ZNeQYHcZ4HfxV7heLC3XfneANmkZksWvo4c8'
SUBSTRATE_ACC4_KSM_ADDR = 'EDNfVHuNHrXsVTLMMNbp6Con5zESZJa3fkRc93AgahuMm99'
SUBSTRATE_ACC5_PUBLIC_KEY = '0x1e24a0ae488fe10725b59887a63d5a7f82cf9f43401363a814168d44accb6b0a'
SUBSTRATE_ACC5_DOT_ADDR = '1gXKQA8JDTjetR759QGGXX98siY4AvaCdp35bswUiuGormc'
SUBSTRATE_ACC5_KSM_ADDR = 'DFqqPEw4oDBy1E2tDAK2L3zRr18AYBcaWvJJyAYQS6FNFzG'

# ENS domain bruno.eth dataset
# https://app.ens.domains/name/bruno.eth
ENS_BRUNO = 'bruno.eth'
ENS_BRUNO_ETH_ADDR = '0xB9b8EF61b7851276B0239757A039d54a23804CBb'
ENS_BRUNO_BTC_BYTES = '76a9147f1fff38da2809b9368262284e0608dfb5c4537988ac'
ENS_BRUNO_BTC_ADDR = '1CbB9YvEFUbb2mXb2jZJQ9Vj9Hasg9XGz8'
# Both Kusama (434) and Polkadot (354) coinType return the substrate public key
ENS_BRUNO_SUBSTRATE_PUBLIC_KEY = '0aff6865635ae11013a83835c019d44ec3f865145943f487ae82a8e7bed3a66b'  # noqa: E501
ENS_BRUNO_KSM_ADDR = 'CpjsLDC1JFyrhm3ftC9Gs4QoyrkHKhZKtK7YqGTRFtTafgp'
ENS_BRUNO_DOT_ADDR = '1FRMM8PEiWXYax7rpS6X4XZX1aAAxSWx1CrKTyrVYhV24fg'

KUSAMA_TEST_NODES = (KusamaNodeName.PARITY, )
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
