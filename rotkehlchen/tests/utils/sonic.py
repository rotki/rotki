from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

SONIC_MAINNET_NODE: Final = WeightedNode(
    node_info=(mainnet_node_name := NodeName(
        name='own',
        endpoint='https://rpc.soniclabs.com',
        owned=False,
        blockchain=SupportedBlockchain.SONIC,
    )),
    active=True,
    weight=ONE,
)

SONIC_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'sonic_manager_connect_at_start',
    [(WeightedNode(
        node_info=mainnet_node_name,
        active=True,
        weight=FVal('0.3'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='drpc',
            endpoint='https://sonic.drpc.org',
            owned=False,
            blockchain=SupportedBlockchain.SONIC,
        ),
        active=True,
        weight=FVal('0.2'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='publicnode',
            endpoint='https://sonic-rpc.publicnode.com',
            owned=False,
            blockchain=SupportedBlockchain.SONIC,
        ),
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='onfinality',
            endpoint='https://sonic-mainnet.api.onfinality.io/public',
            owned=False,
            blockchain=SupportedBlockchain.SONIC,
        ),
        active=True,
        weight=FVal('0.25'),
    ),)],
)
