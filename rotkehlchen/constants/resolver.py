from enum import Enum
from typing import Optional

from rotkehlchen.typing import ChecksumEthAddress

EVM_CHAIN_DIRECTIVE = 'eip155'
ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)


class CHAINID(Enum):
    ETHEREUM_CHAIN_IDENTIFIER = '1'
    OPTIMISM_CHAIN_IDENTIFIER = '10'
    BINANCE_CHAIN_IDENTIFIER = '56'
    OKEX_CHAIN_IDENTIFIER = '66'
    XDAI_CHAIN_IDENTIFIER = '100'
    MATIC_CHAIN_IDENTIFIER = '137'
    FANTOM_CHAIN_IDENTIFIER = '250'
    ARBITRIUM_CHAIN_IDENTIFIER = '42161'
    AVALANCHE_CHAIN_IDENTIFIER = '43114'

    @classmethod
    def deserialize_from_coingecko(cls, chain: str) -> 'CHAINID':
        if chain == 'ethereum':
            return CHAINID.ETHEREUM_CHAIN_IDENTIFIER
        if chain == 'binance-smart-chain':
            return CHAINID.BINANCE_CHAIN_IDENTIFIER
        if chain == 'avalanche':
            return CHAINID.AVALANCHE_CHAIN_IDENTIFIER
        if chain == 'polygon-pos':
            return CHAINID.MATIC_CHAIN_IDENTIFIER

        return KeyError


class EvmTokenKind(Enum):
    ERC20 = 'erc20'
    ERC721 = 'erc721'


VALID_EVM_CHAINS = {
    'S': CHAINID.BINANCE_CHAIN_IDENTIFIER,
    'X': CHAINID.AVALANCHE_CHAIN_IDENTIFIER,
}
EVM_CHAINS_TO_DATABASE = {v: k for k, v in VALID_EVM_CHAINS.items()}


def ethaddress_to_identifier(address: ChecksumEthAddress) -> str:
    return ETHEREUM_DIRECTIVE + address


def strethaddress_to_identifier(address: str) -> str:
    return ETHEREUM_DIRECTIVE + address


def evm_address_to_identifier(
    address: str,
    chain: CHAINID,
    token_type: EvmTokenKind,
    collectible_id: Optional[str] = None,
) -> str:
    """Format a EVM token information into the CAIPs identifier format"""
    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain.value}/{token_type.value}:{address}'
    if collectible_id is not None:
        return ident + f'/{collectible_id}'
    return ident


def translate_old_format_to_new(id: str):
    """
    Given a identifier that is either in the _ceth_ format transalate it to the new format,
    otherwise leave it unmodified.
    """
    if id.startswith(ETHEREUM_DIRECTIVE):
        return evm_address_to_identifier(
            id[6:],
            CHAINID.ETHEREUM_CHAIN_IDENTIFIER,
            EvmTokenKind.ERC20,
        )
    return id
