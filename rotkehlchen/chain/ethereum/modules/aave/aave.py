import logging
from typing import TYPE_CHECKING, NamedTuple, Optional

from gevent.lock import Semaphore

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .common import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveLendingBalance,
    _get_reserve_address_decimals,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ReserveData(NamedTuple):
    """Aave v1 and v2 reserve data

    v1: https://docs.aave.com/developers/v/1.0/developing-on-aave/the-protocol/lendingpool#getreservedata
    v2: https://docs.aave.com/developers/the-core-protocol/lendingpool#getreservedata"""  # noqa: E501
    liquidity_rate: FVal
    variable_borrow_rate: FVal
    stable_borrow_rate: FVal


class Aave(EthereumModule):
    """Aave integration module

    https://docs.aave.com/developers/developing-on-aave/the-protocol/
    """

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()
        self.balances_lock = Semaphore()

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> dict[ChecksumEvmAddress, AaveBalances]:
        with self.balances_lock:
            return self._get_balances(given_defi_balances)

    def _get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> dict[ChecksumEvmAddress, AaveBalances]:
        """Retrieves the aave balances

        Receives the defi balances from zerion as an argument. They can either be directly given
        as the defi balances mapping or as a callable that will retrieve the
        balances mapping when executed.
        """
        aave_balances = {}
        reserve_cache: dict[str, ReserveData] = {}

        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            for balance_entry in balance_entries:
                # Aave also has "Aave • Staking" and "Aave • Uniswap Market" but
                # here we are only querying the balances in the lending protocol
                if balance_entry.protocol.name not in ('Aave', 'Aave V2', 'Aave V2 • Variable Debt', 'Aave V2 • Stable Debt'):  # noqa: E501
                    continue

                # Depending on whether it's asset or debt we find what the reserve asset is
                if balance_entry.balance_type == 'Asset':
                    token_address = balance_entry.underlying_balances[0].token_address
                    balance = balance_entry.underlying_balances[0].balance
                else:
                    token_address = balance_entry.base_balance.token_address
                    balance = balance_entry.base_balance.balance

                try:
                    token = EvmToken(ethaddress_to_identifier(token_address))
                except (UnknownAsset, WrongAssetType):
                    log.warning(f'Found aave DeFi balance for unknown token {token_address}. Skipping')  # noqa: E501
                    continue
                reserve_address, _ = _get_reserve_address_decimals(token)

                reserve_data = reserve_cache.get(reserve_address, None)
                if reserve_data is None:

                    if balance_entry.protocol.name == 'Aave':
                        contract = self.ethereum.contracts.contract(string_to_evm_address('0x398eC7346DcD622eDc5ae82352F02bE94C62d119'))  # noqa: E501
                        reserve_result = contract.call(
                            node_inquirer=self.ethereum,
                            method_name='getReserveData',
                            arguments=[reserve_address],
                        )
                        reserve_data = ReserveData(
                            liquidity_rate=FVal(reserve_result[4] / RAY),
                            variable_borrow_rate=FVal(reserve_result[5] / RAY),
                            stable_borrow_rate=FVal(reserve_result[6] / RAY),
                        )
                    else:  # Aave V2
                        contract = self.ethereum.contracts.contract(string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9'))  # noqa: E501
                        reserve_result = contract.call(
                            node_inquirer=self.ethereum,
                            method_name='getReserveData',
                            arguments=[reserve_address],
                        )
                        reserve_data = ReserveData(
                            liquidity_rate=FVal(reserve_result[3] / RAY),
                            variable_borrow_rate=FVal(reserve_result[4] / RAY),
                            stable_borrow_rate=FVal(reserve_result[5] / RAY),
                        )

                    reserve_cache[balance_entry.base_balance.token_symbol] = reserve_data

                if balance_entry.balance_type == 'Asset':
                    lending_map[token] = AaveLendingBalance(
                        balance=balance,
                        apy=reserve_data.liquidity_rate,
                        version=1 if balance_entry.protocol.name == 'Aave' else 2,
                    )
                else:  # 'Debt'
                    borrowing_map[token] = AaveBorrowingBalance(
                        balance=balance,
                        variable_apr=reserve_data.variable_borrow_rate,
                        stable_apr=reserve_data.stable_borrow_rate,
                        version=1 if balance_entry.protocol.name == 'Aave' else 2,
                    )

            if lending_map == {} and borrowing_map == {}:
                # no aave balances for the account
                continue

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)  # type: ignore  # noqa: E501

        return aave_balances

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        with self.database.user_write() as write_cursor:
            self.database.delete_aave_data(write_cursor)
