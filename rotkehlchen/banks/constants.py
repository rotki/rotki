from typing import Final

from rotkehlchen.types import Location

# Banks are registered through the exchange plumbing (credentials, balances, history
# events, query ranges), so every location here is also part of SUPPORTED_EXCHANGES.
SUPPORTED_BANKS: Final = (Location.QONTO,)
