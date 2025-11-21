from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

OPTIMISM_MAINNET_NODE: Final = WeightedNode(
    node_info=(mainnet_node_name := NodeName(
        name='mainnet',
        endpoint='https://mainnet.optimism.io',
        owned=False,
        blockchain=SupportedBlockchain.OPTIMISM,
    )),
    active=True,
    weight=ONE,
)

OPTIMISM_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'optimism_manager_connect_at_start',
    [(WeightedNode(
        node_info=mainnet_node_name,
        active=True,
        weight=FVal('0.3'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='node real',
            # does not offer archive nodes for optimism
            # https://docs.nodereal.io/docs/archive-node
            endpoint='https://opt-mainnet.nodereal.io/v1/e85935b614124789b99aa92930aca9a4',
            owned=True,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=FVal('0.2'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='blast api',
            endpoint='https://optimism-mainnet.public.blastapi.io',
            owned=True,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='ankr',
            endpoint='https://rpc.ankr.com/optimism',
            owned=False,
            blockchain=SupportedBlockchain.OPTIMISM,
        ),
        active=True,
        weight=FVal('0.25'),
    ),)],
)
