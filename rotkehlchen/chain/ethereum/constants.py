from rotkehlchen.chain.ethereum.types import (
    ETHERSCAN_NODE_NAME,
    NodeName,
    WeightedNode,
    string_to_ethereum_address,
)
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

RANGE_PREFIX_ETHTX = 'ethtxs'
RANGE_PREFIX_ETHINTERNALTX = 'ethinternaltxs'
RANGE_PREFIX_ETHTOKENTX = 'ethtokentxs'

MODULES_PACKAGE = 'rotkehlchen.chain.ethereum.modules'
MODULES_PREFIX = MODULES_PACKAGE + '.'
MODULES_PREFIX_LENGTH = len(MODULES_PREFIX)

ZERO_ADDRESS = string_to_ethereum_address('0x0000000000000000000000000000000000000000')
GENESIS_HASH = deserialize_evm_tx_hash('0x' + '0' * 64)  # hash for transactions in genesis block
ETHEREUM_BEGIN = Timestamp(1438269973)

CPT_KRAKEN = 'kraken'

ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
    ),
    weight=ONE,
)
CLOUDFLARE_NODE_NAME = NodeName(
    name='cloudflare',
    endpoint='https://cloudflare-eth.com/',
    owned=False,
)
MYCRYPTO_NODE_NAME = NodeName(
    name='mycrypto',
    endpoint='https://api.mycryptoapi.com/eth',
    owned=False,
)
BLOCKSOUT_NODE_NAME = NodeName(
    name='blockscout',
    endpoint='https://mainnet-nethermind.blockscout.com/',
    owned=False,
)
AVADO_POOL_NODE_NAME = NodeName(
    name='avado pool',
    endpoint='https://mainnet.eth.cloud.ava.do/',
    owned=False,
)

WEIGHTED_ETHEREUM_NODES = (
    WeightedNode(
        node_info=NodeName(
            name='etherscan',
            endpoint='',
            owned=False,
        ),
        weight=FVal(0.3),
    ),
    WeightedNode(
        node_info=MYCRYPTO_NODE_NAME,
        weight=FVal(0.15),
    ),
    WeightedNode(
        node_info=BLOCKSOUT_NODE_NAME,
        weight=FVal(0.05),
    ),
    WeightedNode(
        node_info=AVADO_POOL_NODE_NAME,
        weight=FVal(0.05),
    ),
    WeightedNode(
        node_info=NodeName(
            name='1inch',
            endpoint='https://web3.1inch.exchange',
            owned=False,
        ),
        weight=FVal(0.15),
    ),
    WeightedNode(
        node_info=NodeName(
            name='myetherwallet',
            endpoint='https://nodes.mewapi.io/rpc/eth',
            owned=False,
        ),
        weight=FVal(0.15),
    ),
    WeightedNode(
        node_info=CLOUDFLARE_NODE_NAME,
        weight=FVal(0.15),
    ),
)
