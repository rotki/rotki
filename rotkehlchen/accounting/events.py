import logging
from typing import TYPE_CHECKING, Iterator, List, Optional

from rotkehlchen.accounting.base import AccountingBase
from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.structures import (
    DefiEvent,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.accounting.totals import (
    OVR_DEFI_PNL,
    OVR_LEDGER_ACTIONS_PNL,
    OVR_LOAN_PROFIT,
    OVR_MARGIN_PNL,
    OVR_STAKING_PROFIT,
)
from rotkehlchen.accounting.transactions import TransactionsAccountant
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import get_balance_asset_rate_at_time_zero_if_error
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import TaxableAction

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TaxableEvents():

    def __init__(
            self,
            csv_exporter: CSVExporter,
            evm_tx_decoder: 'EVMTransactionDecoder',
            profit_currency: Asset,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.csv_exporter = csv_exporter
        self.msg_aggregator = msg_aggregator
        # later customized via accountant._customize()
        self.taxable_ledger_actions: List[LedgerActionType] = []
        self.base = AccountingBase(
            profit_currency=profit_currency,
            csv_exporter=csv_exporter,
            msg_aggregator=msg_aggregator,
        )
        self.transactions = TransactionsAccountant(
            evm_tx_decoder=evm_tx_decoder,
            base=self.base,
        )

    def reset(self, profit_currency: Asset, start_ts: Timestamp, end_ts: Timestamp) -> None:
        self.base.reset(profit_currency=profit_currency, start_ts=start_ts, end_ts=end_ts)
        self.transactions.reset()

    @property
    def account_for_assets_movements(self) -> Optional[bool]:
        return self._account_for_assets_movements

    @account_for_assets_movements.setter
    def account_for_assets_movements(self, value: Optional[bool]) -> None:
        self._account_for_assets_movements = value

    def add_loan_gain(
            self,
            location: Location,
            gained_asset: Asset,
            gained_amount: FVal,
            fee_in_asset: Fee,
            lent_amount: FVal,
            open_time: Timestamp,
            close_time: Timestamp,
            link: Optional[str],
            notes: Optional[str],
    ) -> None:
        """Account for gains from the given loan
        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """

        timestamp = close_time
        rate = self.base.get_rate_in_profit_currency(gained_asset, timestamp)

        net_gain_amount = gained_amount - fee_in_asset
        gain_in_profit_currency = net_gain_amount * rate
        assert gain_in_profit_currency > 0, "Loan profit is negative. Should never happen"
        self.base.cost_basis.obtain_asset(
            location=location,
            timestamp=timestamp,
            description='loan gain',
            asset=gained_asset,
            amount=net_gain_amount,
            rate=rate,
            fee_in_profit_currency=ZERO,
        )
        # count profits if we are inside the query period
        if timestamp >= self.base.query_start_ts:
            log.debug(
                'Accounting for loan profit',
                location=location,
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
            )

            self.base.pnls[OVR_LOAN_PROFIT] += gain_in_profit_currency
            self.csv_exporter.add_loan_profit(
                location=location,
                gained_asset=gained_asset,
                gained_amount=gained_amount,
                gain_in_profit_currency=gain_in_profit_currency,
                lent_amount=lent_amount,
                open_time=open_time,
                close_time=close_time,
                link=link,
                notes=notes,
            )

    def add_margin_position(self, margin: MarginPosition) -> None:
        """Account for the given margin position

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the external service.
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        pl_currency_rate = self.base.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)  # noqa: E501
        fee_currency_rate = self.base.get_rate_in_profit_currency(margin.pl_currency, margin.close_time)  # noqa: E501
        net_gain_loss_in_profit_currency = (
            margin.profit_loss * pl_currency_rate - margin.fee * fee_currency_rate
        )

        # Add or remove to the pl_currency asset
        if margin.profit_loss > 0:
            self.base.cost_basis.obtain_asset(
                location=margin.location,
                timestamp=margin.close_time,
                description='margin position',
                asset=margin.pl_currency,
                amount=margin.profit_loss,
                rate=pl_currency_rate,
                fee_in_profit_currency=ZERO,
            )
        elif margin.profit_loss < 0:
            self.base.cost_basis.reduce_asset_amount(
                asset=margin.pl_currency,
                amount=-margin.profit_loss,
                timestamp=margin.close_time,
            )

        # Reduce the fee_currency asset
        self.base.cost_basis.reduce_asset_amount(asset=margin.fee_currency, amount=margin.fee, timestamp=margin.close_time)  # noqa: E501

        # count profit/loss if we are inside the query period
        if margin.close_time >= self.base.query_start_ts:
            self.base.pnls[OVR_MARGIN_PNL] += net_gain_loss_in_profit_currency

            log.debug(
                'Accounting for margin position',
                notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                net_gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
            )

            self.csv_exporter.add_margin_position(
                location=margin.location,
                margin_notes=margin.notes,
                gain_loss_asset=margin.pl_currency,
                gain_loss_amount=margin.profit_loss,
                gain_loss_in_profit_currency=net_gain_loss_in_profit_currency,
                timestamp=margin.close_time,
                link=margin.link,
                notes=margin.notes,
            )

    def add_defi_event(self, event: DefiEvent) -> None:
        event_description = str(event)
        log.debug(
            'Processing DeFi event',
            event=event_description,
        )

        # count cost basis regardless of being in query time range
        if event.count_spent_got_cost_basis:
            if event.got_asset is not None:
                assert event.got_balance is not None, 'got_balance cant be missing for got_asset'
                # With this we use the calculated usd_value to get the usd rate
                rate = get_balance_asset_rate_at_time_zero_if_error(
                    balance=event.got_balance,
                    asset=self.base.profit_currency,
                    timestamp=event.timestamp,
                    location_hint=event_description,
                    msg_aggregator=self.msg_aggregator,
                )
                # we can also use the commented out code to use oracle query
                # rate = self.base.get_rate_in_profit_currency(entry.asset, event.timestamp)

                self.base.cost_basis.obtain_asset(
                    location=Location.BLOCKCHAIN,
                    timestamp=event.timestamp,
                    description=event_description,
                    asset=event.got_asset,
                    amount=event.got_balance.amount,
                    rate=rate,
                    fee_in_profit_currency=ZERO,
                )

            if event.spent_asset is not None:
                assert event.spent_balance is not None, 'spent_balance cant be missing for spent_asset'  # noqa: E501
                result = self.base.cost_basis.reduce_asset_amount(
                    asset=event.spent_asset,
                    amount=event.spent_balance.amount,
                    timestamp=event.timestamp,
                )
                if not result:
                    log.critical(
                        f'No documented acquisition found for {event.spent_asset} before '
                        f'{self.csv_exporter.timestamp_to_date(event.timestamp)}',
                    )

        elif event.pnl is not None:
            # if we don't count got/spent in cost basis then we should at least count pnl
            for entry in event.pnl:
                if entry.balance.amount > ZERO:
                    # With this we use the calculated usd_value to get the usd rate
                    rate = get_balance_asset_rate_at_time_zero_if_error(
                        balance=entry.balance,
                        asset=self.base.profit_currency,
                        timestamp=event.timestamp,
                        location_hint=event_description,
                        msg_aggregator=self.msg_aggregator,
                    )
                    # we can also use the commented out code to use oracle query
                    # rate = self.get_rate_in_profit_currency(entry.asset, event.timestamp)
                    self.base.cost_basis.obtain_asset(
                        location=Location.BLOCKCHAIN,
                        timestamp=event.timestamp,
                        description=event_description,
                        asset=entry.asset,
                        amount=entry.balance.amount,
                        rate=rate,
                        fee_in_profit_currency=ZERO,
                    )
                else:
                    self.base.cost_basis.reduce_asset_amount(
                        asset=entry.asset,
                        amount=-entry.balance.amount,
                        timestamp=event.timestamp,
                    )

        if event.timestamp < self.base.query_start_ts:
            return

        # now we are within the range. Count profit/loss if any
        profit_loss_list = []
        log.debug(
            'Accounting for DeFi event',
            event=event_description,
        )

        if event.pnl is not None:
            for entry in event.pnl:
                # With this we use the calculated usd_value to get the usd rate
                rate = get_balance_asset_rate_at_time_zero_if_error(
                    balance=entry.balance,
                    asset=self.base.profit_currency,
                    timestamp=event.timestamp,
                    location_hint=event_description,
                    msg_aggregator=self.msg_aggregator,
                )
                # we can also use the commented out code to use oracle query
                # rate = self.base.get_rate_in_profit_currency(entry.asset, event.timestamp)

                single_profit_loss = entry.balance.amount * rate
                log.debug(f'Counting profit/loss for {event_description}: {single_profit_loss}')
                profit_loss_list.append(single_profit_loss)
                self.base.pnls[OVR_DEFI_PNL] += single_profit_loss

        self.csv_exporter.add_defi_event(
            event=event,
            profit_loss_in_profit_currency_list=profit_loss_list,
        )

    def add_ledger_action(self, action: LedgerAction) -> None:
        # should never happen, should be stopped at the main loop
        assert action.timestamp <= self.base.query_end_ts, (
            'Ledger action time > query_end_ts found in processing'
        )
        # calculate the profit currency rate
        if action.rate is None or action.rate_asset is None:
            rate = self.base.get_rate_in_profit_currency(action.asset, action.timestamp)
        else:
            if action.rate_asset == self.base.profit_currency:
                rate = action.rate
            else:
                quote_rate = self.base.get_rate_in_profit_currency(action.rate_asset, action.timestamp)  # noqa: E501
                rate = action.rate * quote_rate

        profit_loss = action.amount * rate
        account_for_action = (
            action.timestamp > self.base.query_start_ts and
            action.action_type in self.taxable_ledger_actions
        )
        log.debug(
            'Processing LedgerAction',
            action=action,
            rate_used=rate,
            account_for_action=account_for_action,
        )
        if account_for_action is False:
            profit_loss = ZERO

        if action.is_profitable():
            self.base.pnls[OVR_LEDGER_ACTIONS_PNL] += profit_loss
            self.base.cost_basis.obtain_asset(
                location=action.location,
                timestamp=action.timestamp,
                description=f'{str(action.action_type)}',
                asset=action.asset,
                amount=action.amount,
                rate=rate,
                fee_in_profit_currency=ZERO,
            )
        else:
            self.base.pnls[OVR_LEDGER_ACTIONS_PNL] -= profit_loss

            self.base.cost_basis.reduce_asset_amount(
                asset=action.asset,
                amount=action.amount,
                timestamp=action.timestamp,
            )

        if action.timestamp > self.base.query_start_ts:
            self.csv_exporter.add_ledger_action(
                action=action,
                profit_loss_in_profit_currency=profit_loss,
            )

    def _process_kraken_staking(self, action: HistoryBaseEntry) -> None:
        timestamp = action.get_timestamp_in_sec()
        rate = self.base.get_rate_in_profit_currency(
            asset=action.asset,
            timestamp=timestamp,
        )

        self.base.cost_basis.obtain_asset(
            location=action.location,
            timestamp=timestamp,
            description=str(action),
            asset=action.asset,
            amount=action.balance.amount,
            rate=rate,
            fee_in_profit_currency=ZERO,
        )
        profit_loss = action.balance.amount * rate
        self.base.pnls[OVR_STAKING_PROFIT] += profit_loss

        self.csv_exporter.add_staking_reward(
            action=action,
            profit_loss_in_profit_currency=profit_loss,
        )

    def add_history_base_entry(
            self,
            action: HistoryBaseEntry,
            actions_iterator: Iterator[TaxableAction],
    ) -> int:
        """Process history base entry and return amount of actions consumed from the iterator"""
        if action.location == Location.KRAKEN:
            if (
                action.event_type != HistoryEventType.STAKING or
                action.event_subtype != HistoryEventSubType.REWARD
            ):
                return 1

            # else
            self._process_kraken_staking(action)
            return 1

        # else
        return self.transactions.process_transaction_event(action, actions_iterator)
