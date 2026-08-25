from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

SONIC_GENESIS: Final = Timestamp(1733011200)
SONIC_MULTICALL_ADDRESS: Final = string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')  # noqa: E501

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x5b6932A2446a2a4d225c0dDdd9b96f4835091cd6')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 100000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('9.934439076382809')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x7924a2dec9fed614731a4cb4d8f46d7ed9c2c6afc6ca353fc87b9b7d694f0259')  # noqa: E501

CPT_SONIC: Final = 'sonic'
SONIC_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_SONIC,
    label='Sonic',
    image='sonic.svg',
)

# BalanceScanner is not deployed on Sonic, so get_multi_balance queries each
# account individually. Deploy BalanceScanner on Sonic first?
