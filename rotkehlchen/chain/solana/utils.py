import logging
from enum import IntEnum
from typing import Final, NamedTuple

from base58 import b58decode
from construct import Struct
from construct.core import ConstructError
from solders.solders import Pubkey, UiCompiledInstruction
from spl.token._layouts import ACCOUNT_LAYOUT, MINT_LAYOUT

from rotkehlchen.chain.solana.types import SolanaInstruction
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress
from rotkehlchen.utils.misc import bytes_to_solana_address
from rotkehlchen.utils.network import request_get_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# AccountType is u8 (1 byte)
# https://github.com/solana-program/token-2022/blob/main/interface/src/extension/mod.rs#L1033
ACCOUNT_TYPE_SIZE: Final = 1

MINT_SIZE: Final = 82  # MINT_LAYOUT.sizeof()
ACCOUNT_SIZE: Final = 165  # ACCOUNT_LAYOUT.sizeof()


class AccountType(IntEnum):
    """Solana Account types.
    https://github.com/solana-program/token-2022/blob/main/interface/src/extension/mod.rs#L1035
    """
    UNINITIALIZED = 0
    MINT = 1
    ACCOUNT = 2


class ExtensionType(IntEnum):
    """Extensions that may be applied to mints or accounts. Only including the ones we use for now.
    https://github.com/solana-program/token-2022/blob/main/interface/src/extension/mod.rs#L1056
    """
    METADATA_POINTER = 18
    TOKEN_METADATA = 19


class TokenStandard(IntEnum):
    """Token standards used in Metaplex metadata.
    https://developers.metaplex.com/token-metadata/token-standard
    """
    NON_FUNGIBLE = 0
    FUNGIBLE_ASSET = 1  # Also called semi-fungible, generally classed as an NFT
    FUNGIBLE = 2  # Normal token
    NON_FUNGIBLE_EDITION = 3
    PROGRAMMABLE_NON_FUNGIBLE = 4


class MintInfo(NamedTuple):
    """Mint information. Only including the fields we use for now.
    See unpack_mint for the full structure.
    """
    supply: int
    decimals: int
    tlv_data: bytes | None


class TokenAccountInfo(NamedTuple):
    """Token account information parsed from ACCOUNT_LAYOUT.
    Contains the essential fields from an SPL Token account.
    """
    mint: SolanaAddress
    owner: SolanaAddress
    amount: int


class MetadataInfo(NamedTuple):
    """Token metadata information. Only including the fields we use for now.
    Decoded from several different layouts in decode_token_metadata.
    """
    name: str
    symbol: str
    uri: str
    token_standard: TokenStandard | None = None  # only present for metaplex metadata


def deserialize_mint(mint_data: bytes) -> MintInfo:
    """Unpacks the mint data from calling getAccountInfo on a token's mint address.
    Full structure is as follows:
    * Main mint info (82 bytes) parsed via MINT_LAYOUT:
        - u32 mintAuthorityOption (4 bytes)
        - publicKey mintAuthority (32 bytes)
        - u64 supply (8 bytes)
        - u8 decimals (1 byte)
        - bool isInitialized (1 byte)
        - u32 freezeAuthorityOption (4 bytes)
        - publicKey freezeAuthority (32 bytes)
    * Empty/optional data (83 bytes) - total 165 bytes (ACCOUNT_SIZE)
    * Account type (1 byte)
    * Extensions data (variable size) in TLV (Type Length Value) format
    https://github.com/solana-program/token-2022/blob/main/clients/js-legacy/src/state/mint.ts#L52

    May raise DeserializationError if the data is invalid.
    """
    if len(mint_data) < MINT_SIZE:
        raise DeserializationError(
            f'Solana token mint data must be at least {MINT_SIZE} bytes, '
            f'only got {len(mint_data)} bytes.',
        )

    try:
        parsed_mint_data = MINT_LAYOUT.parse(mint_data)
    except ConstructError as e:
        raise DeserializationError(f'Failed to parse solana token mint data due to {e!s}') from e

    return MintInfo(
        supply=parsed_mint_data.supply,
        decimals=parsed_mint_data.decimals,
        tlv_data=(
            mint_data[ACCOUNT_SIZE + ACCOUNT_TYPE_SIZE:]
            if len(mint_data) > ACCOUNT_SIZE and mint_data[ACCOUNT_SIZE] == AccountType.MINT
            else None
        ),
    )


def get_extension_data(extension_type: ExtensionType, tlv_data: bytes) -> bytes | None:
    """Gets the raw data for the specified extension from the TLV (Type Length Value) data.
    TLV data is in the following format:
    * extension type (2 bytes)
    * length (2 bytes)
    * data (length bytes)
    """
    offset = 0
    while (data_offset := offset + 4) < len(tlv_data):
        ext_type = int.from_bytes(tlv_data[offset:offset + 2], byteorder='little')
        data_len = int.from_bytes(tlv_data[offset + 2:offset + 4], byteorder='little')
        if ext_type == extension_type:
            return tlv_data[data_offset:data_offset + data_len]
        offset = data_offset + data_len

    return None


def decode_metadata_pointer(data: bytes) -> SolanaAddress | None:
    """Decodes the metadata pointer extension data from the following structure:
    * pubkey authority (32 bytes)
    * pubkey metadata_address (32 bytes)
    https://github.com/solana-program/token-2022/blob/main/interface/src/extension/metadata_pointer/mod.rs
    Returns the metadata address or None if the data is invalid.
    """
    if len(data) < 64:
        return None

    try:
        return bytes_to_solana_address(data[32:64])
    except DeserializationError:
        return None


def decode_token_metadata(data: bytes, layout: Struct) -> MetadataInfo:
    """Decodes raw token metadata using the specified layout.
    If the token_standard field is not present, it is set to None.
    May raise DeserializationError if the data is invalid.
    """
    try:
        raw_metadata = layout.parse(data)
        token_standard = None
        if (raw_token_standard := raw_metadata.get('token_standard')) is not None:
            try:
                token_standard = TokenStandard(raw_token_standard)
            except ValueError:
                log.error(
                    f'Unknown token standard value {raw_token_standard} '
                    f'found in solana token metadata',
                )
                # Don't return here. The token_standard will be set to None, and other heuristics
                # will be used to determine if the token is an NFT.

        return MetadataInfo(
            name=raw_metadata.name.decode('utf-8').strip('\x00'),
            symbol=raw_metadata.symbol.decode('utf-8').strip('\x00'),
            uri=raw_metadata.uri.decode('utf-8').strip('\x00'),
            token_standard=token_standard,
        )
    except (ConstructError, UnicodeDecodeError) as e:
        raise DeserializationError(f'Failed to parse solana token metadata due to {e!s}') from e


def get_metadata_account(token_address: SolanaAddress, metadata_program: Pubkey) -> Pubkey:
    """Get the PDA (Program Derived Address) for the given token address and metadata program."""
    return Pubkey.find_program_address(
        seeds=[b'metadata', bytes(metadata_program), bytes(Pubkey.from_string(token_address))],
        program_id=metadata_program,
    )[0]  # return only address from tuple[address, nonce]


def is_solana_token_nft(
        token_address: SolanaAddress,
        mint_info: MintInfo,
        metadata: MetadataInfo,
) -> bool:
    """Determine if a solana token is an NFT using the provided mint info and metadata.

    Uses the following heuristics to determine if the token is an NFT:
    - the token_standard field in the metadata if present (only in Metaplex metadata)
    - if the decimals are not zero then it is not an NFT
    - if the decimals are zero and supply is one then it is an NFT
    - if decimals are zero but supply is greater than one, check if the offchain metadata
      looks like a semi-fungible NFT.

    Returns a boolean indicating if the token is an NFT.
    """
    if metadata.token_standard is not None:
        return metadata.token_standard != TokenStandard.FUNGIBLE  # all other standards are NFTs
    if mint_info.decimals != 0:  # decimals > 0 is always a normal fungible token
        return False
    if mint_info.supply == 1:  # decimals = 0 and supply = 1 is always an NFT
        return True

    # decimals == 0 and supply > 1 - could be either a semi-fungible (classed as NFT) or
    # simply a normal fungible token with zero decimals (rare but possible)
    # Check if the offchain metadata contains NFT specific data.
    try:
        offchain_metadata = request_get_dict(metadata.uri)
    except (RemoteError, UnableToDecryptRemoteData) as e:
        # Since normal fungible tokens with zero decimals are quite rare, assume it's an NFT
        # if the offchain metadata is unavailable.
        log.warning(
            f'Failed to query offchain metadata for solana token {token_address} due to {e}. '
            f'Assuming it is a semi-fungible NFT since it has 0 decimals and supply > 1.',
        )
        return True

    if any(k in offchain_metadata for k in ('attributes', 'collection', 'properties')):
        return True

    log.debug(
        f'Found solana token {token_address} with 0 decimals and supply > 1 but its '
        f'offchain metadata does not look like a semi-fungible NFT. '
        f'Classing it as a normal fungible token.',
    )
    return False


def lamports_to_sol(amount: int) -> FVal:
    """One SOL is 1e9 lamports. Similar concept as wei in the Ethereum ecosystem"""
    return FVal(amount / 1_000_000_000)


def deserialize_solana_instruction_from_rpc(
        raw_instruction: UiCompiledInstruction,
        account_keys: list[SolanaAddress],
        execution_index: int,
        parent_execution_index: int | None = None,
) -> SolanaInstruction:
    """Deserialize a solana instruction from the RPC response.
    May raise:
    - IndexError if the instruction accounts or program_id_index are out of range
    - ValueError if the data contains invalid base58 characters
    """
    return SolanaInstruction(
        execution_index=execution_index,
        parent_execution_index=parent_execution_index,
        accounts=[account_keys[i] for i in raw_instruction.accounts],
        data=b58decode(raw_instruction.data),
        program_id=account_keys[raw_instruction.program_id_index],
    )


def deserialize_token_account(account_data: bytes) -> TokenAccountInfo:
    """Deserializes token account data into a TokenAccountInfo structure.

    Token account structure (165 bytes):
    - mint: publicKey (32 bytes)
    - owner: publicKey (32 bytes)
    - amount: u64 (8 bytes)
    - delegate_option: u32 (4 bytes)
    - delegate: publicKey (32 bytes)
    - state: u8 (1 byte)
    - is_native_option: u32 (4 bytes)
    - is_native: u64 (8 bytes)
    - delegated_amount: u64 (8 bytes)
    - close_authority_option: u32 (4 bytes)
    - close_authority: publicKey (32 bytes)
    https://github.com/solana-program/token/blob/998ad67a017b64e6030e695d358d7f6cbc476ac5/interface/src/state.rs#L87

    May raise:
    - DeserializationError if the data is invalid.
    """
    if len(account_data) < ACCOUNT_SIZE:
        raise DeserializationError(
            f'Solana token account data must be at least {ACCOUNT_SIZE} bytes, '
            f'got {len(account_data)} bytes.',
        )

    try:
        decoded = ACCOUNT_LAYOUT.parse(account_data)
    except ConstructError as e:
        raise DeserializationError(f'Failed to parse solana token account data due to {e!s}') from e  # noqa: E501

    return TokenAccountInfo(
        mint=bytes_to_solana_address(decoded.mint),
        owner=bytes_to_solana_address(decoded.owner),
        amount=decoded.amount,
    )
