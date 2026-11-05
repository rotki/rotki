from typing import Final

from rotkehlchen.banks.manifest import BankConnectorType

FINTS_PRODUCT_ID: Final = '9F4B31EB21BEEA0D29EB5BAB5'


SUPPORTED_BANK_CONNECTORS: Final = tuple(BankConnectorType)


def bank_connector_module(connector: BankConnectorType) -> str:
    """The module implementing a bank connector, imported only once a connection needs it."""
    return f'rotkehlchen.banks.{connector!s}'
