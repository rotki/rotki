from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

BASE_ETHERSCAN_NODE_NAME = 'base etherscan'
BASE_GENESIS = Timestamp(1686789347)
BASE_ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=BASE_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.BASE,
    ),
    weight=ONE,
    active=True,
)

CPT_BASE = 'base'

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0x3a9e669d9e2d0171c8a057031a9e9C048b7FEE60')
ARCHIVE_NODE_CHECK_BLOCK = 4084762
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.01')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0xc7e021f71a972940c2728717f058f49833e3aa4d074c3599054530f108c281b2')  # noqa: E501
