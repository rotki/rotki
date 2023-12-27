import logging
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple, cast

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.modules.aave.constants import CPT_AAVE_V1, CPT_AAVE_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_ms_to_sec

from .common import (
    AaveBalances,
    AaveBorrowingBalance,
    AaveLendingBalance,
    AaveStats,
    asset_to_atoken,
    get_reserve_address_decimals,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ReserveData(NamedTuple):
    """Aave v1 and v2 reserve data

    v1: https://docs.aave.com/developers/v/1.0/developing-on-aave/the-protocol/lendingpool#getreservedata
    v2: https://docs.aave.com/developers/the-core-protocol/lendingpool#getreservedata"""
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
            premium: Premium | None,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()
        self.balances_lock = Semaphore()
        self.counterparties = [CPT_AAVE_V1, CPT_AAVE_V2]

    def get_balances(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
    ) -> dict[ChecksumEvmAddress, AaveBalances]:
        with self.balances_lock:
            return self._get_balances(given_defi_balances)

    def _get_balances(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
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
                if balance_entry.protocol.name not in {'Aave', 'Aave V2', 'Aave V2 • Variable Debt', 'Aave V2 • Stable Debt'}:  # noqa: E501
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
                reserve_address, _ = get_reserve_address_decimals(token)

                reserve_data = reserve_cache.get(reserve_address)
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

            aave_balances[account] = AaveBalances(lending=lending_map, borrowing=borrowing_map)  # type: ignore

        return aave_balances

    def _calculate_loss(
            self,
            user_address: ChecksumEvmAddress,
            events: list[EvmEvent],
            balances: AaveBalances,
    ) -> tuple[dict[Asset, Balance], dict[Asset, Balance], dict[Asset, Balance]]:
        """
        Returns a tuple of mapping of losses due to liquidation/borrowing and
        earnings due to keeping the principal repaid by the liquidation
        """
        historical_borrow_balances: dict[Asset, FVal] = defaultdict(FVal)
        total_lost: dict[Asset, Balance] = defaultdict(Balance)
        total_earned: dict[Asset, Balance] = defaultdict(Balance)
        atokens_balances: dict[Asset, Balance] = defaultdict(Balance)
        earned_atoken_balances: dict[Asset, Balance] = defaultdict(Balance)
        prev_balance = Balance()

        for event in events:
            if event.asset in earned_atoken_balances:
                prev_balance = earned_atoken_balances[event.asset]

            if event.event_subtype in (HistoryEventSubType.GENERATE_DEBT, HistoryEventSubType.DEPOSIT_ASSET):  # noqa: E501
                historical_borrow_balances[event.asset] -= event.balance.amount
            elif event.event_subtype in (HistoryEventSubType.PAYBACK_DEBT, HistoryEventSubType.REMOVE_ASSET, HistoryEventSubType.REWARD):  # noqa: E501
                if event.event_subtype == HistoryEventSubType.REWARD:
                    atokens_balances[event.asset] += event.balance
                else:
                    if event.extra_data is not None and 'is_liquidation' in event.extra_data:
                        total_earned[event.asset] += event.balance
                    historical_borrow_balances[event.asset] += event.balance.amount
            elif event.event_subtype == HistoryEventSubType.LIQUIDATE:
                # At liquidation you lose the collateral asset
                total_lost[event.asset] += event.balance
            elif event.event_subtype == (HistoryEventSubType.GENERATE_DEBT, HistoryEventSubType.RECEIVE_WRAPPED):  # noqa: E501
                atokens_balances[event.asset] += event.balance
            elif event.event_subtype == (HistoryEventSubType.PAYBACK_DEBT, HistoryEventSubType.RETURN_WRAPPED):  # noqa: E501
                atokens_balances[event.asset] -= event.balance

            if event.asset in atokens_balances:
                amount_diff = atokens_balances[event.asset].amount - prev_balance.amount
                usd_price = query_usd_price_zero_if_error(
                    asset=event.asset,
                    time=ts_ms_to_sec(event.timestamp),
                    location=f'aave interest event {event.event_identifier} from history',
                    msg_aggregator=self.msg_aggregator,
                )
                earned_atoken_balances[event.asset] += Balance(amount=amount_diff, usd_value=amount_diff * usd_price)  # noqa: E501

        for borrowed_asset, amount in historical_borrow_balances.items():
            borrow_balance = balances.borrowing.get(cast(CryptoAsset, borrowed_asset), None)
            this_amount = abs(amount)  # the amount is always <= 0 as it represents a debt position that can get repaid but we need it positive for the calculations  # noqa: E501
            if borrow_balance is not None:
                this_amount += borrow_balance.balance.amount

            usd_price = Inquirer().find_usd_price(borrowed_asset)
            total_lost[borrowed_asset] = Balance(
                # add total_lost amount in case of liquidations
                amount=total_lost[borrowed_asset].amount + this_amount,
                usd_value=this_amount * usd_price,
            )

        # calculate the earned interest
        self._calculate_interest_and_profit(
            user_address=user_address,
            balances=balances,
            total_earned_atokens=earned_atoken_balances,
        )
        return total_lost, total_earned, earned_atoken_balances

    def _calculate_interest_and_profit(
            self,
            user_address: ChecksumEvmAddress,
            balances: AaveBalances,
            total_earned_atokens: dict[Asset, Balance],
    ) -> None:
        """
        Calcualte total earned from aave events. `total_earned_atokens` is modified inside
        this function
        """
        atoken_abi = atoken_v2_abi = None
        # Take aave unpaid interest into account
        for balance_asset, lending_balance in balances.lending.items():
            atoken = asset_to_atoken(balance_asset, version=lending_balance.version)
            if atoken is None:
                log.error(
                    f'Could not find corresponding v{lending_balance.version} aToken to '
                    f'{balance_asset.identifier} during an aave graph unpaid interest '
                    f'query. Skipping entry...',
                )
                continue

            if lending_balance.version == 1:
                method = 'principalBalanceOf'
                if atoken_abi is None:
                    atoken_abi = self.ethereum.contracts.abi('ATOKEN')
                abi = atoken_abi
            else:
                method = 'scaledBalanceOf'
                if atoken_v2_abi is None:
                    atoken_v2_abi = self.ethereum.contracts.abi('ATOKEN_V2')
                abi = atoken_v2_abi

            principal_balance = self.ethereum.call_contract(
                contract_address=atoken.evm_address,
                abi=abi,
                method_name=method,
                arguments=[user_address],
            )
            unpaid_interest = lending_balance.balance.amount - (principal_balance / (FVal(10) ** FVal(atoken.decimals_or_default())))  # noqa: E501
            usd_price = Inquirer().find_usd_price(atoken)
            total_earned_atokens[atoken] += Balance(
                amount=unpaid_interest,
                usd_value=unpaid_interest * usd_price,
            )

    def _get_stats_for_address(
            self,
            address: ChecksumEvmAddress,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            aave_balances: AaveBalances,
    ) -> AaveStats | None:
        db = DBHistoryEvents(self.database)
        query_filter = EvmEventFilterQuery.make(
            counterparties=self.counterparties,
            location_labels=[address],
            event_subtypes=[
                HistoryEventSubType.DEPOSIT_ASSET,
                HistoryEventSubType.REMOVE_ASSET,
                HistoryEventSubType.GENERATE_DEBT,
                HistoryEventSubType.PAYBACK_DEBT,
                HistoryEventSubType.LIQUIDATE,
                HistoryEventSubType.REWARD,
                HistoryEventSubType.RETURN_WRAPPED,
                HistoryEventSubType.RECEIVE_WRAPPED,
            ],
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        with self.database.conn.read_ctx() as cursor:
            events = db.get_history_events(
                cursor=cursor,
                filter_query=query_filter,
                has_premium=self.premium is not None,
                group_by_event_ids=False,
            )

        if len(events) == 0:
            return None

        total_lost, total_earned, earned_interest = self._calculate_loss(
            events=events,
            user_address=address,
            balances=aave_balances,
        )
        return AaveStats(
            total_earned_interest=earned_interest,
            total_lost=total_lost,
            total_earned_liquidations=total_earned,
        )

    def get_stats_for_addresses(
            self,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
    ) -> dict[ChecksumEvmAddress, AaveStats]:
        """
        Calculate the profit and losses in aave v1 and v2 for the provided addresses
        in the time window requested.
        We use the `given_defi_balances` that contain the aave balances to also include
        in the calculations the current aave balances.
        If an address has no information in aave it is not returned in the result mapping.
        We return:
        - total_earned_interest: The total earned is essentially the sum of all interest payments
        plus the difference between ``balanceOf`` and ``principalBalanceOf`` for each asset.
        - total_lost: The total losst for each asset is essentially the accrued interest from
        borrowing and the collateral lost from liquidations.
        - total_earned_liquidations: A mapping of asset identifier for each repaid asset during
        liquidations.
        """
        aave_balances = self.get_balances(given_defi_balances)
        result = {}
        for address in addresses:
            user_stats = self._get_stats_for_address(
                address=address,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                aave_balances=aave_balances.get(address, AaveBalances({}, {})),
            )
            if user_stats is None:
                continue

            result[address] = user_stats

        return result

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
