import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_STRK
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import StarknetAddress

from .node_inquirer import StarknetInquirer

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StarknetManager(ChainManager[StarknetAddress]):
    """Manager for Starknet blockchain operations"""

    def __init__(
            self,
            node_inquirer: StarknetInquirer,
    ) -> None:
        self.node_inquirer = node_inquirer
        self.database = node_inquirer.database

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
        
        # TODO: Add support for querying token balances
        # For now, we only return native STRK balances
        
        return dict(chain_balances)
