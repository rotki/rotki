from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

BASE_MAINNET_NODE: Final = WeightedNode(
    node_info=(mainnet_node_name := NodeName(
        name='own',
        endpoint='https://mainnet.base.org',
        owned=False,
        blockchain=SupportedBlockchain.BASE,
    )),
    active=True,
    weight=ONE,
)

BASE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'base_manager_connect_at_start',
    [(WeightedNode(
        node_info=mainnet_node_name,
        active=True,
        weight=FVal('0.3'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='blockpi',
            endpoint='https://base.blockpi.network/v1/rpc/public',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=FVal('0.2'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='public node',
            endpoint='https://base.publicnode.com',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='ankr',
            endpoint='https://rpc.ankr.com/base',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=FVal('0.25'),
    ),)],
)
