from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

ROBINHOOD_MAINNET_NODE: Final = WeightedNode(
    node_info=(mainnet_node_name := NodeName(
        name='own',
        endpoint='https://rpc.mainnet.chain.robinhood.com',
        owned=False,
        blockchain=SupportedBlockchain.ROBINHOOD,
    )),
    active=True,
    weight=ONE,
)

ROBINHOOD_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'robinhood_manager_connect_at_start',
    [(WeightedNode(
        node_info=mainnet_node_name,
        active=True,
        weight=FVal('0.3'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='publicnode',
            endpoint='https://robinhood-rpc.publicnode.com',
            owned=False,
            blockchain=SupportedBlockchain.ROBINHOOD,
        ),
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='ordofi',
            endpoint='https://rpc.ordofi.network',
            owned=False,
            blockchain=SupportedBlockchain.ROBINHOOD,
        ),
        active=True,
        weight=FVal('0.25'),
    ),), (WeightedNode(
        node_info=NodeName(
            name='nodeflare',
            endpoint='https://rpc.nodeflare.app/robinhood/public',
            owned=False,
            blockchain=SupportedBlockchain.ROBINHOOD,
        ),
        active=True,
        weight=FVal('0.2'),
    ),)],
)
