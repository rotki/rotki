from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

ONE_RPC_SCROLL_NODE: Final = NodeName(
    name='1rpc',
    endpoint='https://1rpc.io/scroll',
    owned=False,
    blockchain=SupportedBlockchain.SCROLL,
)

SCROLLIO_NODE: Final = NodeName(
    name='scrollio',
    endpoint='https://rpc.scroll.io',
    owned=False,
    blockchain=SupportedBlockchain.SCROLL,
)

ANKR_SCROLL_NODE: Final = NodeName(
    name='ankr',
    endpoint='https://rpc.ankr.com/scroll',
    owned=False,
    blockchain=SupportedBlockchain.SCROLL,
)

SCROLL_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'scroll_manager_connect_at_start',
    [(WeightedNode(
        node_info=ONE_RPC_SCROLL_NODE,
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=SCROLLIO_NODE,
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=ANKR_SCROLL_NODE,
        active=True,
        weight=FVal('0.25'),
    ),)],
)
