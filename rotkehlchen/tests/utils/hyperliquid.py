from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.types import SupportedBlockchain

HYPERLIQUID_PUBLIC_RPC_NODES: Final = (WeightedNode(
    node_info=NodeName(
        name='hyperliquid',
        endpoint='https://rpc.hyperliquid.xyz/evm',
        owned=False,
        blockchain=SupportedBlockchain.HYPERLIQUID,
    ),
    active=True,
    weight=ONE,
),)
