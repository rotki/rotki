from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

GNOSIS_GENESIS = Timestamp(1539024185)

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0xCace5b3c29211740E595850E80478416eE77cA21')
ARCHIVE_NODE_CHECK_BLOCK = 36600
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.000061927000000000')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0xf4658cd1e7e891119a678266fba1d7341fafe52554ed11bdb346162d518d3f31')  # noqa: E501

BRIDGE_QUERIED_ADDRESS_PREFIX = 'gnosisbridge_'
