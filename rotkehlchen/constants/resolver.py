from typing import Final

from rotkehlchen.assets.case_diagnostics import (
    is_case_diagnostics_enabled,
    report_non_checksummed_address,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.serialization.deserialize import deserialize_evm_address
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

# Read once at import. See rotkehlchen/assets/case_diagnostics.py
ASSET_CASE_DIAGNOSTICS: Final = is_case_diagnostics_enabled()


def evm_address_to_identifier(
        address: str,
        chain_id: ChainID,
        token_type: EVM_TOKEN_KINDS_TYPE = TokenKind.ERC20,
        collectible_id: str | None = None,
) -> str:
    """Format EVM token information into the CAIPs identifier format

    The address must already be checksummed. Identifiers are compared exactly, so an
    unchecksummed address here produces an identifier that never matches the canonical one.
    """
    if ASSET_CASE_DIAGNOSTICS:
        report_non_checksummed_address(address)

    ident = f'{EVM_CHAIN_DIRECTIVE}:{chain_id.value}/{token_type!s}:{address}'
    if collectible_id is not None:
        return ident + f'/{collectible_id}'
    return ident


def _split_evm_identifier(identifier: str) -> tuple[str, str, str] | None:
    """Split a CAIPs identifier on `:` and return its three substrings or None if it is invalid."""
    if len(parts := identifier.split(':')) != 3 or parts[0] != EVM_CHAIN_DIRECTIVE:
        return None

    return tuple(parts)  # type: ignore[return-value]  # Checked the len above, will be 3 items.


def identifier_to_evm_address(identifier: str) -> ChecksumEvmAddress | None:
    """Parse CAIPs identifier format and return the EVM address or None on error."""
    if (parts := _split_evm_identifier(identifier)) is None:
        return None

    try:
        return deserialize_evm_address(parts[2].split('/')[0])  # Don't include the token id for erc721  # noqa: E501
    except DeserializationError:
        return None


def identifier_to_evm_chain(identifier: str) -> ChainID | None:
    """Parse CAIPs identifier format and return the EVM chain or None on error."""
    if (parts := _split_evm_identifier(identifier)) is None:
        return None

    try:
        return ChainID.deserialize(int(parts[1].split('/')[0]))
    except (DeserializationError, TypeError, ValueError):
        return None


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
