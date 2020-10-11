import logging
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.makerdao.common import RAY
from rotkehlchen.chain.ethereum.zerion import GIVEN_DEFI_BALANCES
from rotkehlchen.constants.ethereum import AAVE_LENDING_POOL
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .blockchain import AaveBlockchainInquirer
from .common import AaveHistory, _get_reserve_address_decimals
from .graph import AaveGraphInquirer

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


class AaveLendingBalance(NamedTuple):
    """A balance for Aave lending.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    apy: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2),
        }


class AaveBorrowingBalance(NamedTuple):
    """A balance for Aave borrowing.

    Asset not included here since it's the key in the map that leads to this structure
    """
    balance: Balance
    variable_apr: FVal
    stable_apr: FVal

    def serialize(self) -> Dict[str, Union[str, Dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'variable_apr': self.variable_apr.to_percentage(precision=2),
            'stable_apr': self.stable_apr.to_percentage(precision=2),
        }


class AaveBalances(NamedTuple):
    """The Aave balances per account. Using str for symbol since ETH is not a token"""
    lending: Dict[str, AaveLendingBalance]
    borrowing: Dict[str, AaveBorrowingBalance]


def _atoken_to_reserve_asset(atoken: EthereumToken) -> Asset:
    reserve_symbol = atoken.identifier[1:]
    if reserve_symbol == 'SUSD':
        reserve_symbol = 'sUSD'
    return Asset(reserve_symbol)


class Aave(EthereumModule):
    """Aave integration module

    https://docs.aave.com/developers/developing-on-aave/the-protocol/
    """

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: DBHandler,
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
            use_graph: bool = False,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.blockchain_inquirer = AaveBlockchainInquirer(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.graph_inquirer = AaveGraphInquirer(
            ethereum_manager=ethereum_manager,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.use_graph = use_graph
        self.history_lock = Semaphore()
        self.balances_lock = Semaphore()

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, AaveBalances]:
        with self.balances_lock:
            return self._get_balances(given_defi_balances)

    def _get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, AaveBalances]:
        """Retrieves the aave balances

        Receives the defi balances from zerion as an argument. They can either be directly given
        as the defi balances mapping or as a callable that will retrieve the
        balances mapping when executed.
        """
        aave_balances = {}
        reserve_cache: Dict[str, Tuple[Any, ...]] = {}

        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name != 'Aave':
                    continue

                # Depending on whether it's asset or debt we find what the reserve asset is
                if balance_entry.balance_type == 'Asset':
                    asset = balance_entry.underlying_balances[0]
                else:
                    asset = balance_entry.base_balance
                reserve_address, _ = _get_reserve_address_decimals(asset.token_symbol)

                reserve_data = reserve_cache.get(reserve_address, None)
                if reserve_data is None:
                    reserve_data = self.ethereum.call_contract(
                        contract_address=AAVE_LENDING_POOL.address,
                        abi=AAVE_LENDING_POOL.abi,
                        method_name='getReserveData',
                        arguments=[reserve_address],
                    )
                    reserve_cache[balance_entry.base_balance.token_symbol] = reserve_data

                if balance_entry.balance_type == 'Asset':
                    lending_map[asset.token_symbol] = AaveLendingBalance(
                        balance=asset.balance,
                        apy=FVal(reserve_data[4] / RAY),
                    )
                else:  # 'Debt'
                    borrowing_map[asset.token_symbol] = AaveBorrowingBalance(
                        balance=asset.balance,
                        variable_apr=FVal(reserve_data[5] / RAY),
                        stable_apr=FVal(reserve_data[6] / RAY),
                    )

            if lending_map == {} and borrowing_map == {}:
                # no aave balances for the account
                continue

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)

        return aave_balances

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,  # pylint: disable=unused-argument
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """Detects aave historical data for the given addresses"""
        latest_block = self.ethereum.get_latest_block_number()
        with self.history_lock:
            if reset_db_data is True:
                self.database.delete_aave_data()

            if self.use_graph:
                return self.graph_inquirer.get_history_for_addresses(
                    addresses=addresses,
                    to_block=latest_block,
                )
            else:
                return self.blockchain_inquirer.get_history_for_addresses(
                    addresses=addresses,
                    to_block=latest_block,
                )

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass
