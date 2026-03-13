from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

MONAD_GENESIS: Final = Timestamp(1748023402)

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x0Af36644C452D417db34652099E23b5a6cF65b27')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 1582393
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('45000000')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x397954d8e3163101596b977f2849bd37208c4cb5f90ffdd4dd9735b941e4b677')  # noqa: E501

CPT_MONAD: Final = 'monad'
MONAD_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_MONAD,
    label='Monad',
    image='monad.svg',
)
