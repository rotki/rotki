from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

ETHEREUM_ETHERSCAN_NODE_NAME = 'etherscan'

ETH2_DEPOSIT_ADDRESS = string_to_evm_address('0x00000000219ab540356cBB839Cbe05303d7705Fa')
ETHEREUM_GENESIS = Timestamp(1438269973)

CPT_KRAKEN = 'kraken'

DEFAULT_TOKEN_DECIMALS = 18

ETHEREUM_ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=ETHEREUM_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.ETHEREUM,
    ),
    weight=ONE,
    active=True,
)

RAY_DIGITS = 27
RAY = 10**RAY_DIGITS

ETH_MANTISSA = 10 ** DEFAULT_TOKEN_DECIMALS

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0x50532e4Be195D1dE0c2E6DfA46D9ec0a4Fee6861')
ARCHIVE_NODE_CHECK_BLOCK = 87042
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('5.1063307')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')  # noqa: E501

SHAPPELA_TIMESTAMP = 1681338455  # the timestamp of the fork where withdrawals enabled
