from typing import Final

from rotkehlchen.connections.types import ConnectorIdentifier

FINTS_PRODUCT_ID: Final = '9F4B31EB21BEEA0D29EB5BAB5'
QONTO_CONNECTOR: Final = ConnectorIdentifier('qonto')
# FinTS is a connector and never a location. Its connections point at a bank location.
FINTS_CONNECTOR: Final = ConnectorIdentifier('fints')

SUPPORTED_BANKS: Final = (QONTO_CONNECTOR, FINTS_CONNECTOR)
