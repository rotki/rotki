from typing import Final

from rotkehlchen.locations.constants import LOCATION_QONTO
from rotkehlchen.locations.types import LocationIdentifier

FINTS_PRODUCT_ID: Final = '9F4B31EB21BEEA0D29EB5BAB5'
# FinTS is a connector, never a location. Until connections store their connector and their
# institution location separately, FinTS credentials are keyed by this connector identifier.
FINTS_CONNECTOR: Final = LocationIdentifier('fints')

# Banks are registered through the exchange plumbing (credentials, balances, history
# events, query ranges), so every location here is also part of SUPPORTED_EXCHANGES.
SUPPORTED_BANKS: Final = (LOCATION_QONTO, FINTS_CONNECTOR)
