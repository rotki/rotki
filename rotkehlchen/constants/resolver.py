from enum import Enum
from typing import Optional

from rotkehlchen.typing import ChecksumEthAddress

EVM_CHAIN_DIRECTIVE = 'eip155'
ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)

class CHAIN_ID(Enum):
    ETHEREUM_CHAIN_IDENTIFIER = '1'
    BINANCE_CHAIN_IDENTIFIER = '56'
    AVALANCHE_CHAIN_IDENTIFIER = '43114'
    POLYGON_CHAIN_IDENTIFIER = '137'
    XDAI_CHAIN_IDENTIFIER = '100'

class EVM_TOKEN_KIND(Enum):
    ERC20 = 'erc20'
    ERC721 = 'erc721'

def ethaddress_to_identifier(address: ChecksumEthAddress) -> str:
    return ETHEREUM_DIRECTIVE + address


def strethaddress_to_identifier(address: str) -> str:
    return ETHEREUM_DIRECTIVE + address

def evm_address_to_identifier(
    address: str,
    chain: CHAIN_ID,
    token_type: EVM_TOKEN_KIND,
    collectible_id: Optional[str]
) -> str:
    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain.value}/{token_type.value}:{address}'
    if collectible_id:
        return ident + f'/{collectible_id}'
    return ident