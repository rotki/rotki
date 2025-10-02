from typing import Final

from rotkehlchen.types import SolanaAddress

SYSTEM_PROGRAM: Final = SolanaAddress('11111111111111111111111111111111')
NATIVE_TRANSFER_DELIMITER: Final = b'\x02\x00\x00\x00'
