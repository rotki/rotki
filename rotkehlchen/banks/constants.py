from typing import Final

from rotkehlchen.types import Location

FINTS_PRODUCT_ID: Final = 'TODO_REPLACE_WITH_DK_ASSIGNED_ID'

# Banks are registered through the exchange plumbing (credentials, balances, history
# events, query ranges), so every location here is also part of SUPPORTED_EXCHANGES.
SUPPORTED_BANKS: Final = (Location.QONTO, Location.FINTS)
