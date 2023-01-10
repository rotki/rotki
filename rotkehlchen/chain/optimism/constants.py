from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants.misc import ONE
from rotkehlchen.types import SupportedBlockchain, Timestamp

OPTIMISM_ETHERSCAN_NODE_NAME = 'optimism etherscan'

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

OPTIMISM_BEGIN = Timestamp(1611071500)

CPT_OPTIMISM = 'optimism'
