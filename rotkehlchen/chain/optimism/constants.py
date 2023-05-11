from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain, Timestamp, deserialize_evm_tx_hash

OPTIMISM_ETHERSCAN_NODE_NAME = 'optimism etherscan'
OPTIMISM_GENESIS = Timestamp(1636666246)
OPTIMISM_ETHERSCAN_NODE = WeightedNode(
    node_info=NodeName(
        name=OPTIMISM_ETHERSCAN_NODE_NAME,
        endpoint='',
        owned=False,
        blockchain=SupportedBlockchain.OPTIMISM,
    ),
    weight=ONE,
    active=True,
)

CPT_OPTIMISM = 'optimism'

ARCHIVE_NODE_CHECK_ADDRESS = string_to_evm_address('0x76a05Df20bFEF5EcE3eB16afF9cb10134199A921')
ARCHIVE_NODE_CHECK_BLOCK = 74000
ARCHIVE_NODE_CHECK_EXPECTED_BALANCE = FVal('0.05')

PRUNED_NODE_CHECK_TX_HASH = deserialize_evm_tx_hash('0x5e77a04531c7c107af1882d76cbff9486d0a9aa53701c30888509d4f5f2b003a')  # noqa: E501
