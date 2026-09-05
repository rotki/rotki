from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

# Block 0 of this Arbitrum Nitro chain carries a zero timestamp, so use block 1's
ROBINHOOD_GENESIS: Final = Timestamp(1777567931)
ROBINHOOD_MULTICALL_ADDRESS: Final = string_to_evm_address('0xcA11bde05977b3631167028862bE2a173976CA11')  # noqa: E501

# The WETH contract's native balance at a fixed block. WETH is a proxy here, deployed
# by the Arbitrum token bridge, so its ETH balance is the wrapped supply at that block.
ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 10000000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('19788.756836358714866797')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0xb8e15c89e7299525dd75d5d9eabed7c973f66228f2ba7d4a8ef12b0687a15144')  # noqa: E501

CPT_ROBINHOOD: Final = 'robinhood'
