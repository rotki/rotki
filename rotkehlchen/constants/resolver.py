from typing import Final, Optional, Tuple, Type

from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
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

    def serialize_for_db(self) -> str:
        return CHAINS_TO_DB_SYMBOL[self]

    @classmethod
    def deserialize_from_db(cls: Type['ChainID'], value: str) -> 'ChainID':
        """May raise a DeserializationError if something is wrong with the DB data"""
        if not isinstance(value, str):
            raise DeserializationError(
                f'Failed to deserialize ChainID DB value from non string value: {value}',
            )

        symbol_to_chain = {v: k for k, v in CHAINS_TO_DB_SYMBOL.items()}
        chain = symbol_to_chain.get(value)
        if chain is None:
            raise DeserializationError(
                f'Failed to deserialize ChainID DB value from invalid value: {value}',
            )
        return chain


CHAINS_TO_DB_SYMBOL: Final = {
    ChainID.ETHEREUM: 'A',
    ChainID.OPTIMISM: 'B',
    ChainID.BINANCE: 'C',
    ChainID.GNOSIS: 'D',
    ChainID.MATIC: 'E',
    ChainID.FANTOM: 'F',
    ChainID.ARBITRUM: 'G',
    ChainID.AVALANCHE: 'H',
}


def evm_address_to_identifier(
        address: str,
        chain: ChainID,
        token_type: EvmTokenKind,
        collectible_id: Optional[str] = None,
) -> str:
    """Format a EVM token information into the CAIPs identifier format"""
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
    """Given an identefier in the CAIPs format extract from it the address and
    chain of the token.
    May raise:
    - InputError: if the information couldn't be extracted from the identifier.
    - AttributeError: if a string is not used as identifier.
    """
    identifier_parts = identifier.split(':')
    if len(identifier_parts) != 3:
        raise InputError(f'Malformed CAIPs identifier. {identifier}')
    try:
        chain = ChainID(int(identifier_parts[1].split('/')[0]))
    except ValueError as e:
        raise InputError(
            f'Tried to extract chain from CAIPs identifier but had an invalid value {identifier}',
        ) from e
    return (
        string_to_evm_address(identifier_parts[-1]),
        chain,
    )
