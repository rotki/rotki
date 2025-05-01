from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

POLYGON_POS_GENESIS = Timestamp(1590824836)
POLYGON_POS_POL_HARDFORK = Timestamp(1725451200)

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0xc3F60BC338E0Af8f46F52650C813FBD3C071E165')
ARCHIVE_NODE_CHECK_BLOCK = 447
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.000000000000000021')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0xf6c3feac09aa84558510f74af0c9bf7fd51ff15f902f68d51592e09cad8896b2')  # noqa: E501
