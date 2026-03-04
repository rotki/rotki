import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.manager import ChainManagerWithTransactions
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_STRK
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress, Timestamp

from .decoding.decoder import StarknetTransactionDecoder
from .decoding.tools import StarknetDecoderTools
from .node_inquirer import StarknetInquirer
from .transactions import StarknetTransactions

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StarknetManager(ChainManagerWithTransactions[StarknetAddress]):
    """Manager for Starknet blockchain operations"""

    def __init__(
            self,
            node_inquirer: StarknetInquirer,
            premium: 'Premium | None' = None,
    ) -> None:
        self.node_inquirer = node_inquirer
        self.database = node_inquirer.database
        self.transactions = StarknetTransactions(
            node_inquirer=self.node_inquirer,
            database=node_inquirer.database,
            voyager=node_inquirer.voyager,
        )
        self.transactions_decoder = StarknetTransactionDecoder(
            database=node_inquirer.database,
            node_inquirer=self.node_inquirer,
            transactions=self.transactions,
            base_tools=StarknetDecoderTools(
                database=self.database,
                node_inquirer=self.node_inquirer,
            ),
            premium=premium,
        )

    def get_balance(self, address: StarknetAddress) -> FVal:
        """Get the native STRK balance for an address

        May raise:
        - RemoteError if there's a problem querying the RPC
        """
        return self.node_inquirer.get_balance(address)

    def get_multi_balance(self, addresses: Sequence[StarknetAddress]) -> dict[StarknetAddress, FVal]:  # noqa: E501
        """Get native STRK balances for multiple addresses

        May raise:
        - RemoteError if there's a problem querying the RPC
        """
        result = {}
        for address in addresses:
            try:
                balance = self.get_balance(address)
                result[address] = balance
                log.debug(f'Starknet balance for {address}: {balance} STRK')
            except Exception as e:
                log.error(f'Failed to query balance for Starknet address {address}: {e}')
                result[address] = ZERO

        return result

    def query_balances(
            self,
            addresses: Sequence[StarknetAddress],
    ) -> dict[StarknetAddress, BalanceSheet]:
        """Query all balances (native + tokens) for the given addresses

        May raise:
        - RemoteError if there's a problem querying the RPC
        """
        chain_balances: defaultdict[StarknetAddress, BalanceSheet] = defaultdict(BalanceSheet)

        # Get native STRK token price
        native_token_price = Inquirer.find_main_currency_price(A_STRK)

        # Query native STRK balances
        for address, balance in self.get_multi_balance(addresses).items():
            if balance != ZERO:
                chain_balances[address].assets[A_STRK][DEFAULT_BALANCE_LABEL] = Balance(
                    amount=balance,
                    value=balance * native_token_price,
                )
                log.debug(
                    f'Starknet address {address} has {balance} STRK '
                    f'(${balance * native_token_price})',
                )

        return dict(chain_balances)

    def query_transactions(
            self,
            addresses: list[StarknetAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query the transactions for the given addresses and save them to the DB.

        May raise RemoteError if there is a problem with querying the external service.
        """
        for address in addresses:
            self.transactions.query_transactions_for_address(address=address)
