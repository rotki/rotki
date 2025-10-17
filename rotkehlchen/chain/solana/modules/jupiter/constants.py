from typing import Final

from rotkehlchen.types import SolanaAddress

CPT_JUPITER: Final = 'jupiter'
JUPITER_AGGREGATOR_PROGRAM_V6: Final = SolanaAddress('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4')
JUPITER_RFQ_ORDER_ENGINE_PROGRAM: Final = SolanaAddress('61DFfeTKM7trxYcPQCM78bJ794ddZprZpAwAnLiwTpYH')  # noqa: E501
# Solana instruction discriminators used by Jupiter program
ROUTE_DISCRIMINATOR: Final = b'\xe5\x17\xcb\x97z\xe3\xad*'  # v1 route instruction
ROUTE_V2_DISCRIMINATOR: Final = b'\xbbd\xfa\xcc1\xc4\xaf\x14'  # v2 route instruction
FILL_DISCRIMINATOR: Final = b'\xa8`\xb7\xa3\\\n(\xa0'  # RFQ fill instruction
SWAP_EVENT_DISCRIMINATOR: Final = b'@\xc6\xcd\xe8&\x08q\xe2'
SWAPS_EVENT_DISCRIMINATOR: Final = b'\x98/N\xeb\xc0`nj'
