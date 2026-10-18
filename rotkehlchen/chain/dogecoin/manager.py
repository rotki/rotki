import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.dogechain import Dogechain
from rotkehlchen.externalapis.sochain import SoChain
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BTCAddress, SupportedBlockchain

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DogecoinManager(ChainManager[BTCAddress]):
    """Tracks the DOGE balances of dogecoin addresses. They are queried from SoChain, and
    from Dogechain if SoChain fails, the way the bitcoin managers go through their APIs."""

    def __init__(self) -> None:
        self.asset = Asset(SupportedBlockchain.DOGECOIN.get_native_token_id())
        self.sochain = SoChain(network='DOGE')
        self.dogechain = Dogechain()

    def _query_amounts(self, addresses: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
        """Query the DOGE balance of every address from the first API that answers for all
        of them. Both APIs answer for one address per request, so the addresses are queried
        one after the other.

        May raise:
        - RemoteError if the queries to all the APIs fail. It includes each API's error.
        """
        errors: dict[str, str] = {}
        for api in (self.sochain, self.dogechain):
            try:
                return {address: api.get_balance(address) for address in addresses}
            except RemoteError as e:
                log.debug('Dogecoin balances query to %s failed due to %s. Trying next API.', api.name, e)  # noqa: E501
                errors[api.name] = str(e)

        serialized_errors = ', '.join(f'{source} error is: "{error}"' for source, error in errors.items())  # noqa: E501
        raise RemoteError(
            f'External {SupportedBlockchain.DOGECOIN!s} request failed for all available '
            f'APIs. {serialized_errors}',
        )

    def query_balances(self, addresses: Sequence[BTCAddress]) -> dict[BTCAddress, BalanceSheet]:
        """Query the DOGE balance of each address.

        May raise:
        - RemoteError if no API could answer for all of the addresses.
        """
        price = Inquirer.find_main_currency_price(self.asset)
        balances: dict[BTCAddress, BalanceSheet] = {}
        for address, amount in self._query_amounts(addresses).items():
            balances[address] = BalanceSheet()
            balances[address].assets[self.asset][DEFAULT_BALANCE_LABEL] = Balance(
                amount=amount,
                value=amount * price,
            )

        return balances
