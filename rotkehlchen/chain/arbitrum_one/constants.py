from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

ARBITRUM_ONE_GENESIS = Timestamp(1622240000)
CPT_ARBITRUM_ONE = 'arbitrum_one'

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
ARCHIVE_NODE_CHECK_BLOCK = 30000000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('193202.532175151892842673')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0x7eef161b36d4f4708fd82d6c050c0b970a1d321f6dcf2c4591dc039f74cc1ab5')  # noqa: E501

ARBITRUM_ONE_CPT_DETAILS = CounterpartyDetails(
    identifier=CPT_ARBITRUM_ONE,
    label='Arbitrum One',
    image='arbitrum_one.svg',
)
