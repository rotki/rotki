from rotkehlchen.types import (
    EVM_TOKEN_KINDS_TYPE,
    SOLANA_TOKEN_KINDS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    SolanaAddress,
    TokenKind,
)

ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)
EVM_CHAIN_DIRECTIVE = 'eip155'
SOLANA_CHAIN_DIRECTIVE = 'solana'


def evm_address_to_identifier(
        address: str,
        chain_id: ChainID,
        token_type: EVM_TOKEN_KINDS_TYPE = TokenKind.ERC20,
        collectible_id: str | None = None,
) -> str:
    """Format EVM token information into the CAIPs identifier format"""
    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain_id.value}/{token_type!s}:{address}'
    if collectible_id is not None:
        return ident + f'/{collectible_id}'
    return ident


def tokenid_to_collectible_id(identifier: str) -> str | None:
    """Get erc721 collectible id from the asset identifier."""
    if 'erc721' not in identifier or len(id_parts := identifier.split('/')) != 3:
        return None

    return id_parts[-1]


def tokenid_belongs_to_collection(token_identifier: str, collection_identifier: str) -> bool:
    """Determine if an ERC721 token belongs to the specified collection.
    An ERC721 token's identifier is its token id appended to its collection identifier.
    Returns true if the token identifier starts with the collection identifier otherwise false.
    """
    return token_identifier.startswith(collection_identifier)


def ethaddress_to_identifier(address: ChecksumEvmAddress) -> str:
    return evm_address_to_identifier(
        address=str(address),
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )


def strethaddress_to_identifier(address: str) -> str:
    return evm_address_to_identifier(
        address=str(address),
        chain_id=ChainID.ETHEREUM,
        token_type=TokenKind.ERC20,
    )


def solana_address_to_identifier(
        address: SolanaAddress,
        token_type: SOLANA_TOKEN_KINDS_TYPE = TokenKind.SPL_TOKEN,
) -> str:
    """Converts a Solana address and token type into a CAIP-19 identifier.

    Uses 'solana' prefix instead of full CAIP-2 chain reference to save database space.

    Example: SPL_TOKEN becomes 'solana/token:<address>'.
    See: https://namespaces.chainagnostic.org/solana/caip19
    """
    return f'{SOLANA_CHAIN_DIRECTIVE}/{str(token_type)[4:]}:{address}'
