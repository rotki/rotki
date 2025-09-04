from typing import Final

from construct import Bytes, GreedyBytes, Int8ul, Int32ul, Prefixed, Struct
from solders.pubkey import Pubkey

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
)
