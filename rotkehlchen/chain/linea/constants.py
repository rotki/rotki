from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

LINEA_GENESIS: Final = Timestamp(1670496243)
LINEA_MULTICALL_ADDRESS: Final = string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')  # noqa: E501

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0xef23B98C5b2bf0544D777A26314A6c4F3b23d749')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 1000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('0.605')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0xf214855883840ce3b30951632cccef71608748677115ae5ec34c3bd4d49a8700')  # noqa: E501

CPT_LINEA: Final = 'linea'
