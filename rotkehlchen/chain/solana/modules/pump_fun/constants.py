from typing import Final

from rotkehlchen.types import SolanaAddress

CPT_PUMP_FUN: Final = 'pump-fun'

PUMP_FEES_PROGRAM: Final = SolanaAddress('pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ')
PUMP_FUN_AMM: Final = SolanaAddress('pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA')

BUY_EVENT_DISCRIMINATOR: Final = b'g\xf4R\x1f,\xf5ww'
GET_FEES_DISCRIMINATOR: Final = b'\xe7%~U\xcf[?4'
