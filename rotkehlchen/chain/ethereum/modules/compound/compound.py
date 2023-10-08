import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Union

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType
from rotkehlchen.assets.asset import Asset, CryptoAsset, EvmToken
from rotkehlchen.assets.utils import symbol_to_evm_token
from rotkehlchen.chain.ethereum.constants import ETH_MANTISSA
from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_COMP, A_ETH
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import BlockchainQueryError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator

ADDRESS_TO_ASSETS = dict[ChecksumEvmAddress, dict[Asset, Balance]]
BLOCKS_PER_DAY = 4 * 60 * 24
DAYS_PER_YEAR = 365


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CompoundBalance(NamedTuple):
    balance_type: BalanceType
    balance: Balance
    apy: Optional[FVal]

    def serialize(self) -> dict[str, Union[Optional[str], dict[str, str]]]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2) if self.apy else None,
        }


def _compound_symbol_to_token(symbol: str, timestamp: Timestamp) -> EvmToken:
    """
    Turns a compound symbol to an ethereum token.

    May raise UnknownAsset
    """
    if symbol == 'cWBTC':
        if timestamp >= Timestamp(1615751087):
            return EvmToken('eip155:1/erc20:0xccF4429DB6322D5C611ee964527D42E5d685DD6a')
        # else
        return EvmToken('eip155:1/erc20:0xC11b1268C1A384e55C48c2391d8d480264A3A7F4')
    # else
    return symbol_to_evm_token(symbol)


class Compound(EthereumModule):
    """Compound integration module

    https://compound.finance/docs#guides
    """

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Optional['Premium'],
            msg_aggregator: 'MessagesAggregator',
    ):
        self.database = database
        self.ethereum = ethereum_inquirer
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.comp = A_COMP.resolve_to_evm_token()

    def _get_apy(self, address: ChecksumEvmAddress, supply: bool) -> Optional[FVal]:
        method_name = 'supplyRatePerBlock' if supply else 'borrowRatePerBlock'

        try:
            rate = self.ethereum.call_contract(
                contract_address=address,
                abi=self.ethereum.contracts.abi('CTOKEN'),
                method_name=method_name,
            )
        except (RemoteError, BlockchainQueryError) as e:
            log.error(f'Could not query cToken {address} for supply/borrow rate: {e!s}')
            return None

        apy = ((FVal(rate) / ETH_MANTISSA * BLOCKS_PER_DAY) + 1) ** (DAYS_PER_YEAR - 1) - 1
        return apy

    def get_balances(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> dict[ChecksumEvmAddress, dict[str, dict[CryptoAsset, CompoundBalance]]]:
        compound_balances = {}
        now = ts_now()
        if isinstance(given_defi_balances, dict):
            defi_balances = given_defi_balances
        else:
            defi_balances = given_defi_balances()

        for account, balance_entries in defi_balances.items():
            lending_map = {}
            borrowing_map = {}
            rewards_map = {}
            for balance_entry in balance_entries:
                if balance_entry.protocol.name not in ('Compound Governance', 'Compound'):
                    continue

                entry = balance_entry.base_balance
                if entry.token_address == ETH_SPECIAL_ADDRESS:
                    asset = A_ETH  # hacky way to specify ETH in compound
                else:
                    try:
                        asset = EvmToken(ethaddress_to_identifier(entry.token_address))
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} with address '
                            f'{entry.token_address} in compound. Skipping',
                        )
                        continue

                unclaimed_comp_rewards = (
                    entry.token_address == self.comp.evm_address and
                    balance_entry.protocol.name == 'Compound Governance'
                )
                if unclaimed_comp_rewards:
                    rewards_map[A_COMP] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=entry.balance,
                        apy=None,
                    )
                    continue

                if balance_entry.balance_type == 'Asset':
                    # Get the underlying balance
                    underlying_token_address = balance_entry.underlying_balances[0].token_address
                    try:
                        underlying_asset = EvmToken(ethaddress_to_identifier(underlying_token_address))  # noqa: E501
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown token with address '
                            f'{underlying_token_address} in compound. Skipping',
                        )
                        continue

                    lending_map[underlying_asset] = CompoundBalance(
                        balance_type=BalanceType.ASSET,
                        balance=balance_entry.underlying_balances[0].balance,
                        apy=self._get_apy(entry.token_address, supply=True),
                    )
                else:  # 'Debt'
                    try:
                        ctoken = _compound_symbol_to_token(
                            symbol='c' + entry.token_symbol,
                            timestamp=now,
                        )
                    except UnknownAsset:
                        log.error(
                            f'Encountered unknown asset {entry.token_symbol} in '
                            f'compound while figuring out cToken. Skipping',
                        )
                        continue

                    borrowing_map[asset] = CompoundBalance(
                        balance_type=BalanceType.LIABILITY,
                        balance=entry.balance,
                        apy=self._get_apy(ctoken.evm_address, supply=False),
                    )

            if lending_map == {} and borrowing_map == {} and rewards_map == {}:
                # no balances for the account
                continue

            compound_balances[account] = {
                'rewards': rewards_map,
                'lending': lending_map,
                'borrowing': borrowing_map,
            }

        return compound_balances  # type: ignore

    def _process_events(
            self,
            events: list[EvmEvent],
            given_defi_balances: GIVEN_DEFI_BALANCES,
    ) -> tuple[ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS]:
        """Processes all events and returns a dictionary of earned balances totals"""
        assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        rewards_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        profit_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        liquidation_profit: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        balances = self.get_balances(given_defi_balances)
        for event in events:
            address = ChecksumEvmAddress(event.location_label)  # type: ignore[arg-type]  # location label is not none here
            if event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET:
                assets[address][event.asset] -= event.balance
            elif event.event_subtype == HistoryEventSubType.GENERATE_DEBT:
                loss_assets[address][event.asset] -= event.balance
            elif event.event_subtype == HistoryEventSubType.REWARD:
                rewards_assets[address][event.asset] += event.balance
            elif event.event_subtype == HistoryEventSubType.REMOVE_ASSET:
                profit_amount = (
                    assets[address][event.asset].amount +
                    event.balance.amount -
                    profit_so_far[address][event.asset].amount
                )
                profit: Optional[Balance]
                if profit_amount >= 0:
                    usd_price = query_usd_price_zero_if_error(
                        asset=event.asset,
                        time=ts_ms_to_sec(event.timestamp),
                        location=f'comp redeem event {event.tx_hash!r} processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far[address][event.asset] += profit
                else:
                    profit = None

                assets[address][event.asset] = event.balance
            elif event.event_subtype == HistoryEventSubType.PAYBACK_DEBT:
                loss_amount = (
                    loss_assets[address][event.asset].amount +
                    event.balance.amount -
                    loss_so_far[address][event.asset].amount
                )
                if loss_amount >= 0:
                    usd_price = query_usd_price_zero_if_error(
                        asset=event.asset,
                        time=ts_ms_to_sec(event.timestamp),
                        location=f'comp repay event {event.tx_hash!r} processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    loss = Balance(loss_amount, loss_amount * usd_price)
                    loss_so_far[address][event.asset] += loss
                else:
                    loss = None

                loss_assets[address][event.asset] = event.balance
            elif event.event_subtype == HistoryEventSubType.LIQUIDATE:
                loss_assets[address][event.asset] += event.balance
                liquidation_profit[address][event.asset] += event.balance

        for address, balance_entry in balances.items():
            # iterate the lending balances to calculate profit based on the current status
            # after the last event
            for asset, entry in balance_entry['lending'].items():
                profit_amount = (
                    profit_so_far[address][asset].amount +
                    entry.balance.amount +
                    assets[address][asset].amount
                )
                if profit_amount < 0:
                    log.error(
                        f'In compound we calculated negative profit. Should not happen. '
                        f'address: {address} asset: {asset} ',
                    )
                    continue

                usd_price = Inquirer().find_usd_price(asset)
                profit_so_far[address][asset] = Balance(
                    amount=profit_amount,
                    usd_value=profit_amount * usd_price,
                )

            # iterate the borrowing balances to calculate loss based on the current status
            # after the last event
            for asset, entry in balance_entry['borrowing'].items():
                remaining = entry.balance + loss_assets[address][asset]
                if remaining.amount < ZERO:
                    continue
                loss_so_far[address][asset] += remaining
                if loss_so_far[address][asset].usd_value < ZERO:
                    amount = loss_so_far[address][asset].amount
                    loss_so_far[address][asset] = Balance(
                        amount=amount, usd_value=amount * Inquirer().find_usd_price(asset),
                    )

            # add pending rewards not collected to the reward assets
            for asset, entry in balance_entry['rewards'].items():
                rewards_assets[address][asset] += entry.balance

        return profit_so_far, loss_so_far, liquidation_profit, rewards_assets

    def get_stats_for_addresses(
            self,
            given_defi_balances: GIVEN_DEFI_BALANCES,
            addresses: list[ChecksumEvmAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> dict[str, Any]:
        """
        Query compound events for the given addresses and process them to obtain statistics
        for profits in compound.
        """
        db = DBHistoryEvents(self.database)
        query_filter = EvmEventFilterQuery.make(
            counterparties=[CPT_COMPOUND],
            location_labels=addresses,  # type: ignore[arg-type]
            event_subtypes=[
                HistoryEventSubType.DEPOSIT_ASSET,
                HistoryEventSubType.GENERATE_DEBT,
                HistoryEventSubType.REWARD,
                HistoryEventSubType.REMOVE_ASSET,
                HistoryEventSubType.LIQUIDATE,
                HistoryEventSubType.PAYBACK_DEBT,
            ],
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        events = []
        with self.database.conn.read_ctx() as cursor:
            events = db.get_history_events(
                cursor=cursor,
                filter_query=query_filter,
                has_premium=self.premium is not None,
                group_by_event_ids=False,
            )
        profit, loss, liquidation, rewards = self._process_events(events, given_defi_balances)
        return {
            'interest_profit': profit,
            'liquidation_profit': liquidation,
            'debt_loss': loss,
            'rewards': rewards,
        }

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
