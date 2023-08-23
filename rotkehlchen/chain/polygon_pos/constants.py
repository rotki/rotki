from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

POLYGON_POS_ETHERSCAN_NODE_NAME = 'polygon pos etherscan'
POLYGON_POS_GENESIS = Timestamp(1590824836)
POLYGON_POS_ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=POLYGON_POS_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.POLYGON_POS,
    ),
    weight=ONE,
    active=True,
)

CPT_POLYGON_POS = 'polygon_pos'

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0xc3F60BC338E0Af8f46F52650C813FBD3C071E165')
ARCHIVE_NODE_CHECK_BLOCK = 447
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.000000000000000021')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0xf6c3feac09aa84558510f74af0c9bf7fd51ff15f902f68d51592e09cad8896b2')  # noqa: E501
