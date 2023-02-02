from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.types import SupportedBlockchain, Timestamp

OPTIMISM_ETHERSCAN_NODE_NAME = 'optimism etherscan'
OPTIMISM_GENESIS = Timestamp(1636666246)
OPTIMISM_ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=OPTIMISM_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.OPTIMISM,
    ),
    weight=ONE,
    active=True,
)

CPT_OPTIMISM = 'optimism'
