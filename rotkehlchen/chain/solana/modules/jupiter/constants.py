from typing import Final

from rotkehlchen.types import SolanaAddress

CPT_JUPITER: Final = 'jupiter'
JUPITER_AGGREGATOR_PROGRAM_V6: Final = SolanaAddress('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4')
JUPITER_RFQ_ORDER_ENGINE_PROGRAM: Final = SolanaAddress('61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH')  # noqa: E501
# Solana instruction discriminators used by Jupiter program
ROUTE_DISCRIMINATOR: Final = b'\xe5\x17\xcb\x97z\xe3\xad*'  # v1 route instruction
ROUTE_V2_DISCRIMINATOR: Final = b'\xbbd\xfa\xcc1\xc4\xaf\x14'  # v2 route instruction
ROUTE_WITH_TOKEN_LEDGER: Final = b'\x96VGt\xa7]\x0eh'
EXACT_OUT_ROUTE_DISCRIMINATOR: Final = b'\xd03\xef\x97{+\xed\\'
EXACT_OUT_ROUTE_V2_DISCRIMINATOR: Final = b'\x9d\x8a\xb8R\x15\xf4\xf3$'
SHARED_ACCOUNTS_ROUTE_DISCRIMINATOR: Final = b'\xc1 \x9b3A\xd6\x9c\x81'
SHARED_ACCOUNTS_ROUTE_V2_DISCRIMINATOR: Final = b'\xd1\x98S\x93|\xfe\xd8\xe9'
SHARED_ACCOUNTS_ROUTE_WITH_TOKEN_LEDGER: Final = b'\xe6y\x8fPw\x9fj\xaa'
SHARED_ACCOUNTS_EXACT_OUT_ROUTE_DISCRIMINATOR: Final = b'\xb0\xd1i\xa8\x9a}E>'
SHARED_ACCOUNTS_EXACT_OUT_ROUTE_V2_DISCRIMINATOR: Final = b'5`\xe5\xca\xd8\xbb\xfa\x18'
FILL_DISCRIMINATOR: Final = b'\xa8`\xb7\xa3\\\n(\xa0'  # RFQ fill instruction
SWAP_EVENT_DISCRIMINATOR: Final = b'@\xc6\xcd\xe8&\x08q\xe2'
SWAPS_EVENT_DISCRIMINATOR: Final = b'\x98/N\xeb\xc0`nj'

# Mapping of route discriminators to the account index of the destination mint
# as defined in the Jupiter aggregator program's IDL:
# https://solscan.io/account/JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4#programIdl
ROUTE_DISCRIMINATORS_TO_MINT_IDX: Final = {
    ROUTE_DISCRIMINATOR: 5,
    ROUTE_V2_DISCRIMINATOR: 4,
    ROUTE_WITH_TOKEN_LEDGER: 5,
    EXACT_OUT_ROUTE_DISCRIMINATOR: 6,
    EXACT_OUT_ROUTE_V2_DISCRIMINATOR: 4,
    SHARED_ACCOUNTS_ROUTE_DISCRIMINATOR: 8,
    SHARED_ACCOUNTS_ROUTE_V2_DISCRIMINATOR: 7,
    SHARED_ACCOUNTS_ROUTE_WITH_TOKEN_LEDGER: 8,
    SHARED_ACCOUNTS_EXACT_OUT_ROUTE_DISCRIMINATOR: 8,
    SHARED_ACCOUNTS_EXACT_OUT_ROUTE_V2_DISCRIMINATOR: 7,
}
