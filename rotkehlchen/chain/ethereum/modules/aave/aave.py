import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, cast

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import AssetBalance, Balance
from rotkehlchen.accounting.structures.defi import DefiEvent, DefiEventType
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.ethereum.modules.makerdao.constants import RAY
from rotkehlchen.constants.ethereum import AAVE_V1_LENDING_POOL, AAVE_V2_LENDING_POOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import ModuleInitializationFailure, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .common import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveHistory,
    AaveLendingBalance,
    _get_reserve_address_decimals,
)
from .graph import AaveGraphInquirer
from .structures import (
    AaveBorrowEvent,
    AaveDepositWithdrawalEvent,
    AaveInterestEvent,
    AaveLiquidationEvent,
    AaveRepayEvent,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
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
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        try:
            self.graph_inquirer = AaveGraphInquirer(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Could not initialize the Aave subgraph due to {str(e)}. '
                f' All aave historical queries are not functioning until this is fixed. '
                f'Probably will get fixed with time. If not report it to rotkis support channel ',
            )
            raise ModuleInitializationFailure('Aave subgraph remote error') from e

        self.history_lock = Semaphore()
        self.balances_lock = Semaphore()

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEvmAddress, AaveBalances]:
        with self.balances_lock:
            return self._get_balances(given_defi_balances)

    def _get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEvmAddress, AaveBalances]:
        """Retrieves the aave balances

        Receives the defi balances from zerion as an argument. They can either be directly given
        as the defi balances mapping or as a callable that will retrieve the
        balances mapping when executed.
        """
        aave_balances = {}
        reserve_cache: Dict[str, ReserveData] = {}

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
                if balance_entry.protocol.name not in ('Aave', 'Aave V2'):
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
                        reserve_result = AAVE_V1_LENDING_POOL.call(
                            manager=self.ethereum,
                            method_name='getReserveData',
                            arguments=[reserve_address],
                        )
                        reserve_data = ReserveData(
                            liquidity_rate=FVal(reserve_result[4] / RAY),
                            variable_borrow_rate=FVal(reserve_result[5] / RAY),
                            stable_borrow_rate=FVal(reserve_result[6] / RAY),
                        )
                    else:  # Aave V2
                        reserve_result = AAVE_V2_LENDING_POOL.call(
                            manager=self.ethereum,
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

    def get_history(
            self,
            addresses: List[ChecksumEvmAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEvmAddress, AaveHistory]:
        """Detects aave historical data for the given addresses"""
        latest_block = self.ethereum.get_latest_block_number()
        with self.history_lock:
            if reset_db_data is True:
                with self.database.user_write() as cursor:
                    self.database.delete_aave_data(cursor)

            aave_balances = self.get_balances(given_defi_balances)
            return self.graph_inquirer.get_history_for_addresses(
                addresses=addresses,
                to_block=latest_block,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                aave_balances=aave_balances,
            )

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: List[ChecksumEvmAddress],
    ) -> List[DefiEvent]:
        if len(addresses) == 0:
            return []

        mapping = self.get_history(
            addresses=addresses,
            reset_db_data=False,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            given_defi_balances={},
        )
        events = []
        for _, history in mapping.items():
            total_borrow: Dict[CryptoAsset, Balance] = defaultdict(Balance)
            realized_borrow_loss: Dict[CryptoAsset, Balance] = defaultdict(Balance)
            for event in history.events:
                got_asset: Optional[CryptoAsset]
                spent_asset: Optional[CryptoAsset]
                pnl = got_asset = got_balance = spent_asset = spent_balance = None
                if event.event_type == 'deposit':
                    event = cast(AaveDepositWithdrawalEvent, event)
                    spent_asset = event.asset
                    spent_balance = event.value
                    # this will need editing for v2
                    got_asset = event.atoken
                    got_balance = event.value
                elif event.event_type == 'withdrawal':
                    event = cast(AaveDepositWithdrawalEvent, event)
                    got_asset = event.asset
                    got_balance = event.value
                    # this will need editing for v2
                    spent_asset = event.atoken
                    spent_balance = got_balance
                elif event.event_type == 'interest':
                    event = cast(AaveInterestEvent, event)
                    pnl = [AssetBalance(asset=event.asset, balance=event.value)]
                elif event.event_type == 'borrow':
                    event = cast(AaveBorrowEvent, event)
                    got_asset = event.asset
                    got_balance = event.value
                    total_borrow[got_asset] += got_balance
                elif event.event_type == 'repay':
                    event = cast(AaveRepayEvent, event)
                    spent_asset = event.asset
                    spent_balance = event.value
                    if total_borrow[spent_asset].amount + realized_borrow_loss[spent_asset].amount < ZERO:  # noqa: E501
                        pnl_balance = total_borrow[spent_asset] + realized_borrow_loss[spent_asset]
                        realized_borrow_loss[spent_asset] += -pnl_balance
                        pnl = [AssetBalance(asset=spent_asset, balance=pnl_balance)]
                elif event.event_type == 'liquidation':
                    event = cast(AaveLiquidationEvent, event)
                    got_asset = event.principal_asset
                    got_balance = event.principal_balance
                    spent_asset = event.collateral_asset
                    spent_balance = event.collateral_balance
                    pnl = [
                        AssetBalance(asset=spent_asset, balance=-spent_balance),
                        AssetBalance(asset=got_asset, balance=got_balance),
                    ]
                    # The principal needs to also be removed from the total_borrow
                    total_borrow[got_asset] -= got_balance

                else:
                    raise AssertionError(f'Unexpected aave event {event.event_type}')
                events.append(DefiEvent(
                    timestamp=event.timestamp,
                    wrapped_event=event,
                    event_type=DefiEventType.AAVE_EVENT,
                    got_asset=got_asset,
                    got_balance=got_balance,
                    spent_asset=spent_asset,
                    spent_balance=spent_balance,
                    pnl=pnl,
                    # Count all aave events in cost basis since there is a swap
                    # involved from normal to aTokens and then back again. Also
                    # borrowing/repaying for debt tracking.
                    count_spent_got_cost_basis=True,
                    tx_hash=event.tx_hash,
                ))

        return events

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        with self.database.user_write() as cursor:
            self.database.delete_aave_data(cursor)
