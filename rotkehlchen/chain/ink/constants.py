from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

INK_GENESIS: Final = Timestamp(1733498411)
INK_MULTICALL_ADDRESS: Final = string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x4200000000000000000000000000000000000006')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 10000000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('1445.425534007868982507')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0xa45a463ae102743b570a77a35bed8299e1c2f8a02499b0977d692cf91f59e6f0')  # noqa: E501

CPT_INK: Final = 'ink'
