from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

SCROLL_GENESIS: Final = Timestamp(1696917600)

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x0A47CeC6657570831AE93db36367656e5597C310')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 485
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('1.000000000000000000')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x93a725e6281bd39c6d3798bb818f280b65e5b40bc017a16ed3d8ad5a29fa636c')  # noqa: E501

CPT_SCROLL: Final = 'scroll'
SCROLL_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_SCROLL,
    label='Scroll',
    image='scroll.svg',
)
