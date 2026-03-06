from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

MONAD_GENESIS: Final = Timestamp(1747232689)
MONAD_MULTICALL_ADDRESS: Final = string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')  # noqa: E501

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x42c15cFA240215D22Aa2B9a6b28c8b48fc7c8Cfa')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 1
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('6000000000')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x397954d8e3163101596b977f2849bd37208c4cb5f90ffdd4dd9735b941e4b677')  # noqa: E501

CPT_MONAD: Final = 'monad'
