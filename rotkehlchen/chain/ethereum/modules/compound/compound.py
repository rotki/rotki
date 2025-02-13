import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.compound.constants import CPT_COMPOUND
from rotkehlchen.chain.ethereum.modules.compound.utils import CompoundBalance
from rotkehlchen.chain.ethereum.modules.compound.v2.compound import CompoundV2
from rotkehlchen.chain.ethereum.modules.compound.v3.compound import CompoundV3
from rotkehlchen.constants import ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import has_premium_check
from rotkehlchen.types import ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_DEFI_BALANCES, GIVEN_ETH_BALANCES
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.premium.premium import Premium
    from rotkehlchen.user_messages import MessagesAggregator

ADDRESS_TO_ASSETS = dict[ChecksumEvmAddress, dict[Asset, Balance]]

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Compound(EthereumModule, CompoundV2, CompoundV3):
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
        CompoundV2.__init__(self, ethereum_inquirer=ethereum_inquirer)
        CompoundV3.__init__(self, ethereum_inquirer=ethereum_inquirer, database=database)
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator

    def get_balances(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            given_eth_balances: 'GIVEN_ETH_BALANCES',
    ) -> dict[ChecksumEvmAddress, dict[str, dict[Asset, CompoundBalance]]]:
        return self.populate_v3_balances(
            given_eth_balances=given_eth_balances,
            compound_balances=self.populate_v2_balances(
                compound_balances=defaultdict(lambda: defaultdict(dict)),
                given_defi_balances=given_defi_balances,
            ),
        )

    def _process_events(
            self,
            events: list[EvmEvent],
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            given_eth_balances: 'GIVEN_ETH_BALANCES',
    ) -> tuple[ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS, ADDRESS_TO_ASSETS]:
        """Processes all events and returns a dictionary of earned balances totals

        This function queries the value of the events on each call. This is for Compound
        in the defi section that will be deprecated.
        """
        assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        rewards_assets: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        profit_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        loss_so_far: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))
        liquidation_profit: ADDRESS_TO_ASSETS = defaultdict(lambda: defaultdict(Balance))

        balances = self.get_balances(
            given_defi_balances=given_defi_balances,
            given_eth_balances=given_eth_balances,
        )
        for event in events:
            usd_price = query_usd_price_zero_if_error(
                asset=event.asset,
                time=event.get_timestamp_in_sec(),
                location=f'comp repay event {event.tx_hash!r} processing',
            )
            address = ChecksumEvmAddress(event.location_label)  # type: ignore[arg-type]  # location label is not none here
            event_balance = Balance(amount=event.amount, usd_value=event.amount * usd_price)
            if event.event_subtype == HistoryEventSubType.DEPOSIT_FOR_WRAPPED:
                assets[address][event.asset] -= event_balance
            elif event.event_subtype == HistoryEventSubType.GENERATE_DEBT:
                loss_assets[address][event.asset] -= event_balance
            elif event.event_subtype == HistoryEventSubType.REWARD:
                rewards_assets[address][event.asset] += event_balance
            elif event.event_subtype == HistoryEventSubType.REDEEM_WRAPPED:
                profit_amount = (
                    assets[address][event.asset].amount +
                    event.amount -
                    profit_so_far[address][event.asset].amount
                )
                profit: Balance | None
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

                assets[address][event.asset] = event_balance
            elif event.event_subtype == HistoryEventSubType.PAYBACK_DEBT:
                loss_amount = (
                    loss_assets[address][event.asset].amount +
                    event.amount -
                    loss_so_far[address][event.asset].amount
                )
                if loss_amount >= 0:
                    loss = Balance(loss_amount, loss_amount * usd_price)
                    loss_so_far[address][event.asset] += loss
                else:
                    loss = None

                loss_assets[address][event.asset] = event_balance
            elif event.event_subtype == HistoryEventSubType.LIQUIDATE:
                loss_assets[address][event.asset] += event_balance
                liquidation_profit[address][event.asset] += event_balance

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

                usd_price = Inquirer.find_usd_price(asset)
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
                        amount=amount, usd_value=amount * Inquirer.find_usd_price(asset),
                    )

            # add pending rewards not collected to the reward assets
            for asset, entry in balance_entry['rewards'].items():
                rewards_assets[address][asset] += entry.balance

        return profit_so_far, loss_so_far, liquidation_profit, rewards_assets

    def get_stats_for_addresses(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            given_eth_balances: 'GIVEN_ETH_BALANCES',
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
                HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                HistoryEventSubType.GENERATE_DEBT,
                HistoryEventSubType.REWARD,
                HistoryEventSubType.REDEEM_WRAPPED,
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
                has_premium=has_premium_check(self.premium),
                group_by_event_ids=False,
            )
        profit, loss, liquidation, rewards = self._process_events(
            events=events,
            given_defi_balances=given_defi_balances,
            given_eth_balances=given_eth_balances,
        )
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
