from typing import Final

from rotkehlchen.constants import ZERO
from rotkehlchen.types import Price, Timestamp

ZERO_PRICE = Price(ZERO)
BITCOIN_GENESIS_BLOCK_TS: Final = Timestamp(1231006505)  # 2009-01-03 18:15:05 UTC
CRYPTOCOMPARE_INVALID_PRICE_TS_CUTOFF: Final = Timestamp(946684800)  # 2000-01-01 00:00:00 UTC
