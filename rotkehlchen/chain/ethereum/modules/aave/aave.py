import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import AssetBalance, Balance, DefiEvent, DefiEventType
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.ethereum.modules.makerdao.constants import RAY
from rotkehlchen.chain.ethereum.structures import (
    AaveBorrowEvent,
    AaveDepositWithdrawalEvent,
    AaveInterestEvent,
    AaveLiquidationEvent,
    AaveRepayEvent,
)
from rotkehlchen.constants.ethereum import AAVE_LENDING_POOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError, UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule

from .blockchain import AaveBlockchainInquirer
from .common import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveHistory,
    AaveLendingBalance,
    _get_reserve_address_decimals,
)
from .graph import AaveGraphInquirer

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


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
            use_graph: bool = True,  # by default use graph
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
        try:
            self.graph_inquirer: Optional[AaveGraphInquirer] = AaveGraphInquirer(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.graph_inquirer = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Aave subgraph due to {str(e)}. '
                f' All aave historical queries are not functioning until this is fixed. '
                f'Probably will get fixed with time. If not report it to rotkis support channel ',
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
                # Aave also has "Aave • Staking" and "Aave • Uniswap Market" but
                # here we are only querying the balances in the lending protocol
                if balance_entry.protocol.name != 'Aave':
                    continue

                # Depending on whether it's asset or debt we find what the reserve asset is
                if balance_entry.balance_type == 'Asset':
                    token_address = balance_entry.underlying_balances[0].token_address
                    balance = balance_entry.underlying_balances[0].balance
                else:
                    token_address = balance_entry.base_balance.token_address
                    balance = balance_entry.base_balance.balance

                try:
                    token = EthereumToken(token_address)
                except UnknownAsset:
                    log.warning('Found aave DeFi balance for unknown token {token_address}. Skipping')  # noqa: E501
                    continue
                reserve_address, _ = _get_reserve_address_decimals(token)

                reserve_data = reserve_cache.get(reserve_address, None)
                if reserve_data is None:
                    reserve_data = AAVE_LENDING_POOL.call(
                        ethereum=self.ethereum,
                        method_name='getReserveData',
                        arguments=[reserve_address],
                    )
                    reserve_cache[balance_entry.base_balance.token_symbol] = reserve_data

                if balance_entry.balance_type == 'Asset':
                    lending_map[token] = AaveLendingBalance(
                        balance=balance,
                        apy=FVal(reserve_data[4] / RAY),
                    )
                else:  # 'Debt'
                    borrowing_map[token] = AaveBorrowingBalance(
                        balance=balance,
                        variable_apr=FVal(reserve_data[5] / RAY),
                        stable_apr=FVal(reserve_data[6] / RAY),
                    )

            if lending_map == {} and borrowing_map == {}:
                # no aave balances for the account
                continue

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)  # type: ignore  # noqa: E501

        return aave_balances

    def get_history(
            self,
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> Dict[ChecksumEthAddress, AaveHistory]:
        """Detects aave historical data for the given addresses"""
        latest_block = self.ethereum.get_latest_block_number()
        with self.history_lock:
            if reset_db_data is True:
                self.database.delete_aave_data()

            if self.use_graph:
                if self.graph_inquirer is None:  # could not initialize graph
                    log.error(
                        "Tried to query Aave's history via the subgraph "
                        "without an initialized graph_inquirer",
                    )
                    return {}

                aave_balances = self.get_balances(given_defi_balances)
                return self.graph_inquirer.get_history_for_addresses(
                    addresses=addresses,
                    to_block=latest_block,
                    from_timestamp=from_timestamp,
                    to_timestamp=to_timestamp,
                    aave_balances=aave_balances,
                )
            # else
            return self.blockchain_inquirer.get_history_for_addresses(
                addresses=addresses,
                to_block=latest_block,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                aave_balances=None,  # type: ignore
            )

    def get_history_events(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: List[ChecksumEthAddress],
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
            total_borrow: Dict[Asset, Balance] = defaultdict(Balance)
            realized_borrow_loss: Dict[Asset, Balance] = defaultdict(Balance)
            for event in history.events:
                got_asset: Optional[Asset]
                spent_asset: Optional[Asset]
                pnl = got_asset = got_balance = spent_asset = spent_balance = None  # noqa: E501
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
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_aave_data()
