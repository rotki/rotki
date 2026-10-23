import logging
from collections import deque
from typing import TYPE_CHECKING, Final

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.concurrency import result_of, spawn, wait
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_DOGE
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

# How many balance requests run at the same time. SoChain answers up to two at a time
# from one IP address without an API key.
MAX_PARALLEL_QUERIES: Final = 2


class DogecoinManager(ChainManager[BTCAddress]):
    """Tracks the DOGE balances of dogecoin addresses. They are queried from SoChain, and
    from Dogechain if SoChain fails, the way the bitcoin managers go through their APIs."""

    def __init__(self) -> None:
        self.asset = A_DOGE
        self.sochain = SoChain(network='DOGE')
        self.dogechain = Dogechain()

    @staticmethod
    def _query_api(
            api: SoChain | Dogechain,
            addresses: Sequence[BTCAddress],
    ) -> tuple[dict[BTCAddress, FVal], RemoteError | None]:
        """Query the DOGE balances of the addresses from one API, MAX_PARALLEL_QUERIES
        at a time, since neither API answers for more than one address per request.
        No more addresses are queried after the API's first failure.

        Returns the balances it answered and the failure, if there was one.
        """
        pending = deque(addresses)
        amounts: dict[BTCAddress, FVal] = {}
        errors: list[RemoteError] = []

        def query_pending() -> None:
            while len(errors) == 0:
                try:
                    address = pending.popleft()
                except IndexError:
                    return

                try:
                    amounts[address] = api.get_balance(address)
                except RemoteError as e:
                    errors.append(e)

        tasks = [spawn(query_pending) for _ in range(min(MAX_PARALLEL_QUERIES, len(addresses)))]
        wait(tasks)
        for task in tasks:
            result_of(task)  # raises anything other than an API failure

        return amounts, errors[0] if len(errors) != 0 else None

    def _query_amounts(self, addresses: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
        """Query the DOGE balance of every address from SoChain, and the balances SoChain
        could not answer from Dogechain, the way the bitcoin managers go through their APIs.

        May raise:
        - RemoteError if no API answered for some of the addresses. It includes each
        API's error.
        """
        amounts: dict[BTCAddress, FVal] = {}
        errors: dict[str, str] = {}
        for api in (self.sochain, self.dogechain):
            found, error = self._query_api(
                api=api,
                addresses=[address for address in addresses if address not in amounts],
            )
            amounts.update(found)
            if error is None:
                return {address: amounts[address] for address in addresses}

            log.debug('Dogecoin balances query to %s failed due to %s. Trying next API.', api.name, error)  # noqa: E501
            errors[api.name] = str(error)

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
