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
    Renamed,
    Struct,
    this,
)

from rotkehlchen.chain.solana.rpc import Hash, Pubkey

SOLANA_GENESIS_BLOCK_HASH: Final = Hash.from_string('4sGjMW1sUnHzSxGspuhpqLDx6wiyjNtZAMdL4VZHirAn')

# Native Solana Stake Program
# https://docs.solanalabs.com/runtime/programs#stake-program
STAKE_PROGRAM_ID: Final = Pubkey.from_string('Stake11111111111111111111111111111111111111')
TOKEN_PROGRAM_ID: Final = Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
TOKEN_2022_PROGRAM_ID: Final = Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')

# Offsets within the stake account data for memcmp filters
STAKE_ACCOUNT_WITHDRAWER_OFFSET: Final = 44  # Authorized.withdrawer pubkey

# Used to derive the metadata PDA (Program Derived Address) for tokens in get_metadata_account
METADATA_PROGRAM_IDS: Final = (
    Pubkey.from_string('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s'),  # Official Metaplex
    Pubkey.from_string('META4s4fSmpkTbZoUsgC1oBnWB31vQcmnN8giPw51Zu'),  # less common, used by catwifhat for example  # noqa: E501
)

# Layout for parsing metadata from the token-2022 TokenMetadata extension
# https://github.com/solana-program/token-metadata/blob/main/interface/src/state.rs#L23
METADATA_LAYOUT_2022: Final = Struct(
    Renamed(Bytes(32), 'update_authority'),
    Renamed(Bytes(32), 'mint'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'name'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'symbol'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'uri'),
)
# Layout for parsing metadata from a token's metadata PDA.
# https://github.com/metaplex-foundation/mpl-token-metadata/blob/main/programs/token-metadata/program/src/state/metadata.rs#L68
# https://github.com/metaplex-foundation/mpl-token-metadata/blob/main/programs/token-metadata/program/src/state/data.rs#L6
METADATA_LAYOUT_LEGACY: Final = Struct(
    Renamed(Int8ul, 'key'),
    Renamed(Bytes(32), 'update_authority'),
    Renamed(Bytes(32), 'mint'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'name'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'symbol'),
    Renamed(Prefixed(Int32ul, GreedyBytes), 'uri'),
    Renamed(Int16ul, 'seller_fee_basis_points'),
    Renamed(Flag, 'creators_flag'),
    Renamed(If(this.creators_flag, Struct(
        Renamed(Int32ul, 'count'),
        Renamed(Array(this.count, Struct(
            Renamed(Bytes(32), 'address'),
            Renamed(Flag, 'verified'),
            Renamed(Int8ul, 'share'),
        )), 'items'),
    )), 'creators'),
    Renamed(Flag, 'primary_sale_happened'),
    Renamed(Flag, 'is_mutable'),
    Renamed(Flag, 'edition_nonce_flag'),
    Renamed(If(this.edition_nonce_flag, Int8ul), 'edition_nonce'),
    Renamed(Flag, 'token_standard_flag'),
    Renamed(If(this.token_standard_flag, Int8ul), 'token_standard'),
)
