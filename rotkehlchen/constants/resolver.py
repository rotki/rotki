from typing import Optional, Tuple

from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.errors.misc import InputError
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind

ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)
EVM_CHAIN_DIRECTIVE = 'eip155'


def evm_address_to_identifier(
        address: str,
        chain: ChainID,
        token_type: EvmTokenKind,
        collectible_id: Optional[str] = None,
) -> str:
    """Format EVM token information into the CAIPs identifier format"""
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
