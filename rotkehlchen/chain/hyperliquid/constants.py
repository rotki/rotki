from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

HYPERLIQUID_GENESIS: Final = Timestamp(1704067200)

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address(
    '0x04b0f18b9b1FF987C5D5e134516f449aA9a2E004',
)
ARCHIVE_NODE_CHECK_BLOCK: Final = 10000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('1.297410355228008636')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash(
    '0x215a5123b5a5e0b22ab258c82bf92c999e5fdf48ebb9f8ab01f0723edba49216',
)
