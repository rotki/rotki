from typing import Optional, Tuple
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress, EvmTokenKind
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)
EVM_CHAIN_DIRECTIVE = 'eip155'


class ChainID(DBEnumMixIn):
    ETHEREUM = 1
    OPTIMISM = 10
    BINANCE = 56
    GNOSIS = 100
    MATIC = 137
    FANTOM = 250
    ARBITRUM = 42161
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


def evm_address_to_identifier(
    address: str,
    chain: ChainID,
    token_type: EvmTokenKind,
    collectible_id: Optional[str] = None,
) -> str:
    """Format an EVM token information into the CAIPs identifier format"""
    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain.value}/{str(token_type)}:{address}'
    if collectible_id is not None:
        return ident + f'/{collectible_id}'
    return ident


def ethaddress_to_identifier(address: ChecksumEvmAddress) -> str:
    return evm_address_to_identifier(
        address=str(address),
        chain=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    )


def strethaddress_to_identifier(address: str) -> str:
    return evm_address_to_identifier(
        address=str(address),
        chain=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    )


def identifier_to_address_chain(identifier: str) -> Tuple[ChecksumEvmAddress, ChainID]:
    identifier_parts = identifier.split(':')
    return (
        string_to_evm_address(identifier_parts[-1]),
        ChainID(int(identifier_parts[1].split('/')[0])),
    )
