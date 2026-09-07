from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.types import SupportedBlockchain

INK_MAINNET_NODE: Final = WeightedNode(
    node_info=NodeName(
        name='gelato',
        endpoint='https://rpc-gel.inkonchain.com',
        owned=False,
        blockchain=SupportedBlockchain.INK,
    ),
    active=True,
    weight=ONE,
)
