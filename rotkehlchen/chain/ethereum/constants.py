from typing import Final

from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

ETHEREUM_ETHERSCAN_NODE_NAME: Final = 'etherscan'

ETH2_DEPOSIT_ADDRESS: Final = string_to_evm_address('0x00000000219ab540356cBB839Cbe05303d7705Fa')
ETHEREUM_GENESIS: Final = Timestamp(1438269973)

CPT_KRAKEN: Final = 'kraken'
CPT_POLONIEX: Final = 'poloniex'
CPT_UPHOLD: Final = 'uphold'

ETHEREUM_ETHERSCAN_NODE: Final = WeightedNode(
    node_info=NodeName(
        name=ETHEREUM_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    weight=ONE,
    active=True,
)

RAY_DIGITS: Final = 27
RAY: Final = 10**RAY_DIGITS

ARCHIVE_NODE_CHECK_ADDRESS: Final = string_to_evm_address('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861')  # noqa: E501
ARCHIVE_NODE_CHECK_BLOCK: Final = 87042
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE: Final = FVal('5.1063307')

PRUNED_NODE_CHECK_TX_HASH: Final = deserialize_evm_tx_hash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')  # noqa: E501

SHAPPELA_TIMESTAMP: Final = 1681338455  # the timestamp of the fork where withdrawals enabled
LAST_GRAPH_DELEGATIONS: Final = 'GRAPH_DELEGATIONS'
