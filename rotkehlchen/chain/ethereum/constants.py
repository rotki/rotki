from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

ETHEREUM_ETHERSCAN_NODE_NAME = 'etherscan'
MODULES_PACKAGE = 'rotkehlchen.chain.ethereum.modules'
MODULES_PREFIX = MODULES_PACKAGE + '.'
MODULES_PREFIX_LENGTH = len(MODULES_PREFIX)

ETH2_DEPOSIT_ADDRESS = string_to_evm_address('0x00000000219ab540356cBB839Cbe05303d7705Fa')
GENESIS_HASH = deserialize_evm_tx_hash('0x' + '0' * 64)  # hash for transactions in genesis block
ETHEREUM_BEGIN = Timestamp(1438269973)

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
