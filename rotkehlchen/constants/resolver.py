from enum import Enum
from typing import Optional

from rotkehlchen.typing import ChecksumEthAddress

EVM_CHAIN_DIRECTIVE = 'eip155'
ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)


class ChainID(Enum):
    ETHEREUM = 1
    OPTIMISM = 10
    BINANCE = 56
    OKEX = 66
    XDAI = 100
    MATIC = 137
    FANTOM = 250
    ARBITRIUM = 42161
    AVALANCHE = 43114

    @classmethod
    def deserialize_from_coingecko(cls, chain: str) -> 'ChainID':
        if chain == 'ethereum':
            return ChainID.ETHEREUM
        if chain == 'binance-smart-chain':
            return ChainID.BINANCE
        if chain == 'avalanche':
            return ChainID.AVALANCHE
        if chain == 'polygon-pos':
            return ChainID.MATIC

        raise RuntimeError(f'Unknown chain {chain}')


class EvmTokenKind(Enum):
    ERC20 = 1
    ERC721 = 2

    def __str__(self) -> str:
        if self == EvmTokenKind.ERC20:
            return 'ERC20'
        if self == EvmTokenKind.ERC721:
            return 'ERC721'
        raise RuntimeError('Invalid value for EvmTokenKind')


VALID_EVM_CHAINS = {
    'S': ChainID.BINANCE,
    'X': ChainID.AVALANCHE,
}
EVM_CHAINS_TO_DATABASE = {v: k for k, v in VALID_EVM_CHAINS.items()}


def ethaddress_to_identifier(address: ChecksumEthAddress) -> str:
    return ETHEREUM_DIRECTIVE + address


def strethaddress_to_identifier(address: str) -> str:
    return ETHEREUM_DIRECTIVE + address


def evm_address_to_identifier(
    address: str,
    chain: ChainID,
    token_type: EvmTokenKind,
    collectible_id: Optional[str] = None,
) -> str:
    """Format an EVM token information into the CAIPs identifier format"""
    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain.value}/{token_type.value}:{address}'
    if collectible_id is not None:
        return ident + f'/{collectible_id}'
    return ident


def translate_old_format_to_new(identifier: str) -> str:
    """
    Given a identifier that is either in the _ceth_ format transalate it to the new format,
    otherwise leave it unmodified.
    """
    if identifier.startswith(ETHEREUM_DIRECTIVE):
        return evm_address_to_identifier(
            identifier[6:],
            ChainID.ETHEREUM,
            EvmTokenKind.ERC20,
        )
    return identifier
