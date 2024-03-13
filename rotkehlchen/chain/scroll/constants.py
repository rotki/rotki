from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

SCROLL_ETHERSCAN_NODE_NAME: Final = 'scroll etherscan'
SCROLL_GENESIS: Final = Timestamp(1696917600)
SCROLL_ETHERSCAN_NODE: Final = WeightedNode(
    node_info=NodeName(
        name=SCROLL_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.SCROLL,
    ),
    weight=ONE,
    active=True,
)

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x0a47cec6657570831ae93db36367656e5597c310')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 485
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('1.000000000000000000')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x93a725e6281bd39c6d3798bb818f280b65e5b40bc017a16ed3d8ad5a29fa636c')  # noqa: E501
