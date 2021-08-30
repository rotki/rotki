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

    @classmethod
    def deserialize_from_coingecko(cls, chain: str) -> 'CHAIN_ID':
        if chain == 'ethereum':
            return CHAIN_ID.ETHEREUM_CHAIN_IDENTIFIER
        if chain == 'binance-smart-chain':
            return CHAIN_ID.BINANCE_CHAIN_IDENTIFIER
        if chain == 'avalanche':
            return CHAIN_ID.AVALANCHE_CHAIN_IDENTIFIER
        if chain == 'polygon-pos':
            return CHAIN_ID.POLYGON_CHAIN_IDENTIFIER
        
        return KeyError

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