from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_SUPERFLUID: Final = 'superfluid'

TOKEN_DOWNGRADED_TOPIC: Final = b';\xc2y\x81\xae\xbb\xb5\x7f\x92G\xdc\x00\xfd\xe9\xd6\xcd\x91\xe4\xb20\x08?\xec28\xfe\xdb\xcb\xa1\xf9\xab='  # noqa: E501
TOKEN_UPGRADED_TOPIC: Final = b'%\xca\x84\x07gs\xb0E]\xb56!\xc4Y\xdd\xc8O\xe4\x08@\xe4\x93*bpj\x03%f\xf3\x99\xdf'  # noqa: E501
FLOW_UPDATED_TOPIC: Final = b'W&\x9d.\xbc\xcc\xec\xdc\xc0\xd9\xd2\xc0\xa0\xb8\x0e\xad\x95\xf3D\xe2\x8e\xc2\x0fP\xf7\t\x81\x1f \x9dN\x0e'  # noqa: E501

# Constant Flow Agreement (CFA) contract addresses
# https://docs.superfluid.org/docs/protocol/contract-addresses
CFA_V1_ADDRESSES: Final = {
    ChainID.ETHEREUM: string_to_evm_address('0x2844c1BBdA121E9E43105630b9C8310e5c72744b'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0x731FdBB12944973B500518aea61942381d7e240D'),
    ChainID.BASE: string_to_evm_address('0x19ba78B9cDB05A877718841c574325fdB53601bb'),
    ChainID.POLYGON_POS: string_to_evm_address('0x6EeE6060f715257b970700bc2656De21dEdF074C'),
    ChainID.OPTIMISM: string_to_evm_address('0x204C6f131bb7F258b2Ea1593f5309911d8E458eD'),
    ChainID.BINANCE_SC: string_to_evm_address('0x49c38108870e74Cb9420C0991a85D3edd6363F75'),
    ChainID.GNOSIS: string_to_evm_address('0xEbdA4ceF883A7B12c4E669Ebc58927FBa8447C7D'),
    ChainID.SCROLL: string_to_evm_address('0xB3bcD6da1eeB6c97258B3806A853A6dcD3B6C00c'),
}
