from rotkehlchen.chain.ethereum.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

MODULES_PACKAGE = 'rotkehlchen.chain.polygon.modules'
MODULES_PREFIX = MODULES_PACKAGE + '.'
MODULES_PREFIX_LENGTH = len(MODULES_PREFIX)

# TODO: Adjust to Polygon
ZERO_ADDRESS = string_to_evm_address('0x0000000000000000000000000000000000000000')
GENESIS_HASH = deserialize_evm_tx_hash('0x' + '0' * 64)  # hash for transactions in genesis block
POLYGON_BEGIN = Timestamp(1438269973)

POLYGONSCAN_NODE_NAME = "polygonscan"
POLYGONSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=POLYGONSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.POLYGON,
    ),
    weight=ONE,
    active=True,
)
