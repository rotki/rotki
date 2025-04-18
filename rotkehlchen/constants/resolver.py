from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind

ETHEREUM_DIRECTIVE = '_ceth_'
ETHEREUM_DIRECTIVE_LENGTH = len(ETHEREUM_DIRECTIVE)
EVM_CHAIN_DIRECTIVE = 'eip155'


def evm_address_to_identifier(
        address: str,
        chain_id: ChainID,
        token_type: EvmTokenKind = EvmTokenKind.ERC20,
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
        token_type=EvmTokenKind.ERC20,
    )


def strethaddress_to_identifier(address: str) -> str:
    return evm_address_to_identifier(
        address=str(address),
        chain_id=ChainID.ETHEREUM,
        token_type=EvmTokenKind.ERC20,
    )
