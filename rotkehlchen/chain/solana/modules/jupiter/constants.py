from typing import Final

from rotkehlchen.types import SolanaAddress

CPT_JUPITER: Final = 'jupiter'
JUPITER_AGGREGATOR_PROGRAM_V6: Final = SolanaAddress('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4')
# Solana instruction discriminators used by Jupiter program
ROUTE_DISCRIMINATOR: Final = b'\xe5\x17\xcb\x97z\xe3\xad*'  # v1 route instruction
ROUTE_V2_DISCRIMINATOR: Final = b'\xbbd\xfa\xcc1\xc4\xaf\x14'  # v2 route instruction
SWAP_EVENT_DISCRIMINATOR: Final = b'\xe4E\xa5.Q\xcb\x9a\x1d@\xc6\xcd\xe8&\x08q\xe2'
SWAP_EVENT_DISCRIMINATOR_LEN: Final = len(SWAP_EVENT_DISCRIMINATOR)
