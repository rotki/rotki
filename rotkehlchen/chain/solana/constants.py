from typing import Final

from construct import (
    Array,
    Bytes,
    Flag,
    GreedyBytes,
    If,
    Int8ul,
    Int16ul,
    Int32ul,
    Prefixed,
    Struct,
    this,
)
from solders.hash import Hash
from solders.pubkey import Pubkey

SOLANA_GENESIS_BLOCK_HASH: Final = Hash.from_string('4sGjMW1sUnHzSxGspuhpqLDx6wiyjNtZAMdL4VZHirAn')

# Used to derive the metadata PDA (Program Derived Address) for tokens in get_metadata_account
METADATA_PROGRAM_IDS: Final = (
    Pubkey.from_string('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'),  # Official Metaplex
    Pubkey.from_string('META4s4fSmpkTbZoUsgC1oBnWB31vQcmnN8giPw51Zu'),  # less common, used by catwifhat for example  # noqa: E501
)

# Layout for parsing metadata from the token-2022 TokenMetadata extension
# https://github.com/solana-program/token-metadata/blob/main/interface/src/state.rs#L23
METADATA_LAYOUT_2022: Final = Struct(
    'update_authority' / Bytes(32),
    'mint' / Bytes(32),
    'name' / Prefixed(Int32ul, GreedyBytes),
    'symbol' / Prefixed(Int32ul, GreedyBytes),
    'uri' / Prefixed(Int32ul, GreedyBytes),
)
# Layout for parsing metadata from a token's metadata PDA.
# https://github.com/metaplex-foundation/mpl-token-metadata/blob/main/programs/token-metadata/program/src/state/metadata.rs#L68  # noqa: E501
# https://github.com/metaplex-foundation/mpl-token-metadata/blob/main/programs/token-metadata/program/src/state/data.rs#L6  # noqa: E501
METADATA_LAYOUT_LEGACY: Final = Struct(
    'key' / Int8ul,
    *METADATA_LAYOUT_2022.subcons,
    'seller_fee_basis_points' / Int16ul,
    'creators_flag' / Flag,
    'creators' / If(this.creators_flag, Struct(
        'count' / Int32ul,
        'items' / Array(this.count, Struct(
            'address' / Bytes(32),
            'verified' / Flag,
            'share' / Int8ul,
        )),
    )),
    'primary_sale_happened' / Flag,
    'is_mutable' / Flag,
    'edition_nonce_flag' / Flag,
    'edition_nonce' / If(this.edition_nonce_flag, Int8ul),
    'token_standard_flag' / Flag,
    'token_standard' / If(this.token_standard_flag, Int8ul),
)
