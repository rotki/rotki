from typing import Final

from spl.token.constants import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID

from rotkehlchen.chain.solana.types import pubkey_to_solana_address
from rotkehlchen.types import SolanaAddress

SPL_TOKEN_PROGRAM: Final = pubkey_to_solana_address(TOKEN_PROGRAM_ID)
TOKEN_2022_PROGRAM: Final = pubkey_to_solana_address(TOKEN_2022_PROGRAM_ID)
SYSTEM_PROGRAM: Final = SolanaAddress('11111111111111111111111111111111')
NATIVE_TRANSFER_DELIMITER: Final = b'\x02\x00\x00\x00'
SPL_TOKEN_TRANSFER_DELIMITER: Final = b'\x03'
SPL_TOKEN_TRANSFER_CHECKED_DELIMITER: Final = b'\x0c'
SPL_TOKEN_TRANSFER_CHECKED_WITH_FEE_DELIMITER: Final = b'\x1a'
SPL_TOKEN_TRANSFER_CHECKED_DELIMITERS: Final = (
    SPL_TOKEN_TRANSFER_CHECKED_DELIMITER,
    SPL_TOKEN_TRANSFER_CHECKED_WITH_FEE_DELIMITER,
)
