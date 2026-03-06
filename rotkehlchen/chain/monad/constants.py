from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

MONAD_GENESIS: Final = Timestamp(1732406400)

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x0000000000000000000000000000000000000001')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 1
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('0')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x0000000000000000000000000000000000000000000000000000000000000001')  # noqa: E501

CPT_MONAD: Final = 'monad'
MONAD_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_MONAD,
    label='Monad',
    image='monad.svg',
)
