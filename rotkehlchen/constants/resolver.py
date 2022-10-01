from typing import Optional

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
