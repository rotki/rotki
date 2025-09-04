from enum import IntEnum
from typing import Final, NamedTuple

from construct import Struct
from construct.core import ConstructError
from solders.solders import Pubkey
from spl.token._layouts import MINT_LAYOUT

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.types import SolanaAddress
from rotkehlchen.utils.misc import bytes_to_solana_address

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


class MintInfo(NamedTuple):
    """Mint information. Only including the fields we use for now.
    See unpack_mint for the full structure.
    """
    supply: int
    decimals: int
    tlv_data: bytes | None


class MetadataInfo(NamedTuple):
    """Token metadata information. Only including the fields we use for now.
    Decoded from several different layouts in decode_token_metadata.
    """
    name: str
    symbol: str


def unpack_mint(mint_data: bytes) -> MintInfo | None:
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
    """
    if len(mint_data) < MINT_SIZE:
        return None

    parsed_mint_data = MINT_LAYOUT.parse(mint_data)
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


def decode_token_metadata(data: bytes, layout: Struct) -> MetadataInfo | None:
    """Decodes raw token metadata using the specified layout.
    Returns a tuple with the name and symbol or None if the data is invalid.
    TODO: Maybe include raw_metadata.uri and use it to query the token image as well?
    https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=127649813
    """
    try:
        raw_metadata = layout.parse(data)
        return MetadataInfo(
            name=raw_metadata.name.decode('utf-8').strip('\x00'),
            symbol=raw_metadata.symbol.decode('utf-8').strip('\x00'),
        )
    except ConstructError:
        return None


def get_metadata_account(token_address: SolanaAddress, metadata_program: Pubkey) -> Pubkey:
    """Get the PDA (Program Derived Address) for the given token address and metadata program."""
    return Pubkey.find_program_address(
        seeds=[b'metadata', bytes(metadata_program), bytes(Pubkey.from_string(token_address))],
        program_id=metadata_program,
    )[0]  # return only address from tuple[address, nonce]


def lamports_to_sol(amount: int) -> FVal:
    """One SOL is 1e9 lamports. Similar concept as wei in the Ethereum ecosystem"""
    return FVal(amount / 1_000_000_000)
