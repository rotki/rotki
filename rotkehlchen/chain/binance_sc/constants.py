from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

BINANCE_SC_GENESIS = Timestamp(1587390414)

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0xf29991AB7C30dC0dAfc4C39Bf1acD7d2534ecC85')
ARCHIVE_NODE_CHECK_BLOCK = 15364859
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('2.075405465759803932')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0xb9fa80f75dc13c921cb1a30c3c9d220625c3fe59bb7dc49082d80b70d95b74d0')  # noqa: E501
