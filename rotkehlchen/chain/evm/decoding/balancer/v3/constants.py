from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

VAULT_ADDRESS: Final = string_to_evm_address('0xbA1333333333a1BA1108E8412f11850A5C319bA9')
LIQUIDITY_ADDED_TOPIC: Final = b'\xa2jR\xd8\xd57\x02\xbb\xa7\xf17\x90{\x8e\x1f\x99\xff\x87\xf6\xd4P\x14Bp\xca%\xe7$\x81\xcc\xa8q'  # noqa: E501
LIQUIDITY_REMOVED_TOPIC: Final = b'\xfb\xe5\xb0\xd7\x9f\xb9O\x1e\x81\xc0\xa9+\xf8j\xe9\xd3\xa1\x9e\x9d\x1b\xf6 ,\r>u\x12\x0fe\xd5\xd8\xa5'  # noqa: E501
BALANCER_V3_POOL_ABI: ABI = [{
    'inputs': [],
    'name': 'getTokens',
    'outputs': [{
      'name': 'tokens',
      'type': 'address[]',
    }],
    'stateMutability': 'view',
    'type': 'function',
}]
BALANCER_V3_SUPPORTED_CHAINS: Final = (
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.GNOSIS,
)
