from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

OPTIMISM_GENESIS: Final = Timestamp(1636666246)
OP_BEDROCK_UPGRADE: Final = Timestamp(1686081600)
CPT_OPTIMISM: Final = 'optimism'

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x76a05Df20bFEF5EcE3eB16afF9cb10134199A921')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 74000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('0.05')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x5e77a04531c7c107af1882d76cbff9486d0a9aa53701c30888509d4f5f2b003a')  # noqa: E501
