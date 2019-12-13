import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import gevent

from rotkehlchen.accounting.events import TaxableEvents
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors import (
    DeserializationError,
    NoPriceForGivenTimestamp,
    PriceQueryUnknownFromAsset,
    UnknownAsset,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Loan,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import Fee, FilePath, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.accounting import (
    TaxableAction,
    action_get_assets,
    action_get_timestamp,
    action_get_type,
)
from rotkehlchen.utils.misc import timestamp_to_date, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Accountant():

    def __init__(
            self,
            db: DBHandler,
            profit_currency: Asset,
            user_directory: FilePath,
            msg_aggregator: MessagesAggregator,
            create_csv: bool,
            include_crypto2crypto: bool,
            taxfree_after_period: Optional[int],
            include_gas_costs: bool,
    ) -> None:
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.csvexporter = CSVExporter(profit_currency, user_directory, create_csv)
        self.events = TaxableEvents(self.csvexporter, profit_currency)
        self.set_main_currency(profit_currency)

        self.asset_movement_fees = FVal(0)
        self.last_gas_price = FVal(0)

        self.started_processing_timestamp = Timestamp(-1)
        self.currently_processing_timestamp = Timestamp(-1)

        # Customizable Options
        self.include_gas_costs = include_gas_costs
        self.events.include_crypto2crypto = include_crypto2crypto
        self.events.taxfree_after_period = taxfree_after_period

    def __del__(self) -> None:
        del self.events
        del self.csvexporter

    @property
    def general_trade_pl(self) -> FVal:
        return self.events.general_trade_profit_loss

    @property
    def taxable_trade_pl(self) -> FVal:
        return self.events.taxable_trade_profit_loss

    def customize(self, settings: ModifiableDBSettings) -> None:
        if settings.include_crypto2crypto is not None:
            self.events.include_crypto2crypto = settings.include_crypto2crypto

        if settings.taxfree_after_period is not None:
            given_taxfree_after_period: Optional[int] = settings.taxfree_after_period
            if given_taxfree_after_period == -1:
                # That means user requested to disable taxfree_after_period
                given_taxfree_after_period = None

            self.events.taxfree_after_period = given_taxfree_after_period

    def set_main_currency(self, currency: Asset) -> None:
        assert currency.is_fiat(), 'main currency checks should happen at marshmallow validation'

        self.profit_currency = currency
        self.events.profit_currency = currency

    @staticmethod
    def query_historical_price(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> FVal:
        price = PriceHistorian().query_historical_price(from_asset, to_asset, timestamp)
        return price

    def get_rate_in_profit_currency(self, asset: Asset, timestamp: Timestamp) -> FVal:
        # TODO: Moved this to events.py too. Is it still needed here?
        if asset == self.profit_currency:
            rate = FVal(1)
        else:
            rate = self.query_historical_price(
                asset,
                self.profit_currency,
                timestamp,
            )
        assert isinstance(rate, (FVal, int))  # TODO Remove. Is temporary assert
        return rate

    def get_fee_in_profit_currency(self, trade: Trade) -> Fee:
        fee_rate = self.query_historical_price(
            from_asset=trade.fee_currency,
            to_asset=self.profit_currency,
            timestamp=trade.timestamp,
        )
        return Fee(fee_rate * trade.fee)

    def add_asset_movement_to_events(self, movement: AssetMovement) -> None:
        timestamp = movement.timestamp
        if timestamp < self.start_ts:
            return

        fee_rate = self.get_rate_in_profit_currency(movement.fee_asset, timestamp)
        cost = movement.fee * fee_rate
        self.asset_movement_fees += cost
        log.debug(
            'Accounting for asset movement',
            sensitive_log=True,
            category=movement.category,
            asset=movement.asset,
            cost_in_profit_currency=cost,
            timestamp=timestamp,
            exchange_name=movement.location,
        )

        self.csvexporter.add_asset_movement(
            exchange=movement.location,
            category=movement.category,
            asset=movement.asset,
            fee=movement.fee,
            rate=fee_rate,
            timestamp=timestamp,
        )

    def account_for_gas_costs(self, transaction: EthereumTransaction) -> None:
        if not self.include_gas_costs:
            return
        if transaction.timestamp < self.start_ts:
            return

        if transaction.gas_price == -1:
            gas_price = self.last_gas_price
        else:
            gas_price = transaction.gas_price
            self.last_gas_price = transaction.gas_price

        rate = self.get_rate_in_profit_currency(A_ETH, transaction.timestamp)
        eth_burned_as_gas = (transaction.gas_used * gas_price) / FVal(10 ** 18)
        cost = eth_burned_as_gas * rate
        self.eth_transactions_gas_costs += cost

        log.debug(
            'Accounting for ethereum transaction gas cost',
            sensitive_log=True,
            gas_used=transaction.gas_used,
            gas_price=gas_price,
            timestamp=transaction.timestamp,
        )

        self.csvexporter.add_tx_gas_cost(
            transaction_hash=transaction.tx_hash,
            eth_burned_as_gas=eth_burned_as_gas,
            rate=rate,
            timestamp=transaction.timestamp,
        )

    def trade_add_to_sell_events(self, trade: Trade, loan_settlement: bool) -> None:
        selling_asset = trade.base_asset
        receiving_asset = trade.quote_asset
        receiving_asset_rate = self.get_rate_in_profit_currency(
            receiving_asset,
            trade.timestamp,
        )
        selling_rate = receiving_asset_rate * trade.rate
        fee_in_profit_currency = self.get_fee_in_profit_currency(trade)
        gain_in_profit_currency = selling_rate * trade.amount

        if not loan_settlement:
            self.events.add_sell_and_corresponding_buy(
                selling_asset=selling_asset,
                selling_amount=trade.amount,
                receiving_asset=receiving_asset,
                receiving_amount=trade.amount * trade.rate,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                trade_rate=trade.rate,
                rate_in_profit_currency=selling_rate,
                timestamp=trade.timestamp,
            )
        else:
            self.events.add_sell(
                selling_asset=selling_asset,
                selling_amount=trade.amount,
                receiving_asset=None,
                receiving_amount=None,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                trade_rate=trade.rate,
                rate_in_profit_currency=selling_rate,
                timestamp=trade.timestamp,
                loan_settlement=True,
                is_virtual=False,
            )

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            trade_history: List[Union[Trade, MarginPosition]],
            loan_history: List[Loan],
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
    ) -> Dict[str, Any]:
        """Processes the entire history of cryptoworld actions in order to determine
        the price and time at which every asset was obtained and also
        the general and taxable profit/loss.

        start_ts here is the timestamp at which to start taking trades and other
        taxable events into account. Not where processing starts from. Processing
        always starts from the very first event we find in the history.
        """
        log.info(
            'Start of history processing',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        self.events.reset(start_ts, end_ts)
        self.last_gas_price = FVal("2000000000")
        self.start_ts = start_ts
        self.eth_transactions_gas_costs = FVal(0)
        self.asset_movement_fees = FVal(0)
        self.csvexporter.reset_csv_lists()
        # Used only in the "avoid zerorpc remote lost after 10ms problem"
        self.last_sleep_ts = 0

        actions: List[TaxableAction] = list(trade_history)
        # If we got loans, we need to interleave them with the full history and re-sort
        if len(loan_history) != 0:
            actions.extend(loan_history)

        if len(asset_movements) != 0:
            actions.extend(asset_movements)

        if len(eth_transactions) != 0:
            actions.extend(eth_transactions)

        actions.sort(
            key=lambda action: action_get_timestamp(action),
        )
        # The first ts is the ts of the first action we have in history or 0 for empty history
        first_ts = Timestamp(0) if len(actions) == 0 else action_get_timestamp(actions[0])
        self.currently_processing_timestamp = first_ts
        self.started_processing_timestamp = first_ts

        prev_time = Timestamp(0)
        count = 0
        for action in actions:
            try:
                (
                    should_continue,
                    prev_time,
                    count,
                ) = self.process_action(action, end_ts, prev_time, count)
            except PriceQueryUnknownFromAsset as e:
                ts = action_get_timestamp(action)
                self.msg_aggregator.add_error(
                    f'Skipping action at '
                    f' {timestamp_to_date(ts, formatstr="%d/%m/%Y, %H:%M:%S")} '
                    f'during history processing due to an asset unknown to '
                    f'cryptocompare being involved. Check logs for details',
                )
                log.error(
                    f'Skipping action {str(action)} during history processing due to '
                    f'cryptocompare not supporting an involved asset: {str(e)}',
                )
                continue
            except NoPriceForGivenTimestamp as e:
                ts = action_get_timestamp(action)
                self.msg_aggregator.add_error(
                    f'Skipping action at '
                    f' {timestamp_to_date(ts, formatstr="%d/%m/%Y, %H:%M:%S")} '
                    f'during history processing due to inability to find a price '
                    f'at that point in time: {str(e)}. Check the logs for more details',
                )
                log.error(
                    f'Skipping action {str(action)} during history processing due to '
                    f'inability to query a price at that time: {str(e)}',
                )
                continue

            if not should_continue:
                break

        self.events.calculate_asset_details()
        Inquirer().save_historical_forex_data()

        sum_other_actions = (
            self.events.margin_positions_profit_loss +
            self.events.loan_profit -
            self.events.settlement_losses -
            self.asset_movement_fees -
            self.eth_transactions_gas_costs
        )
        total_taxable_pl = self.events.taxable_trade_profit_loss + sum_other_actions
        return {
            'overview': {
                'loan_profit': str(self.events.loan_profit),
                'margin_positions_profit_loss': str(self.events.margin_positions_profit_loss),
                'settlement_losses': str(self.events.settlement_losses),
                'ethereum_transaction_gas_costs': str(self.eth_transactions_gas_costs),
                'asset_movement_fees': str(self.asset_movement_fees),
                'general_trade_profit_loss': str(self.events.general_trade_profit_loss),
                'taxable_trade_profit_loss': str(self.events.taxable_trade_profit_loss),
                'total_taxable_profit_loss': str(total_taxable_pl),
                'total_profit_loss': str(
                    self.events.general_trade_profit_loss +
                    sum_other_actions,
                ),
            },
            'all_events': self.csvexporter.all_events,
        }

    def process_action(
            self,
            action: TaxableAction,
            end_ts: Timestamp,
            prev_time: Timestamp,
            count: int,
    ) -> Tuple[bool, Timestamp, int]:
        """Processes each individual action and returns whether we should continue
        looping through the rest of the actions or not"""

        # Hack to periodically yield back to the gevent IO loop to avoid getting
        # the losing remote after hearbeat error for the zerorpc client. (after 10s)
        # https://github.com/0rpc/zerorpc-python/issues/37
        # TODO: Find better way to do this. Perhaps enforce this only if method
        # is a synced call, and if async don't do this yielding. In any case
        # this calculation should definitely be async
        now = ts_now()
        ignored_assets = self.db.get_ignored_assets()
        if now - self.last_sleep_ts >= 7:  # choose 7 seconds to be safe
            self.last_sleep_ts = now
            gevent.sleep(0.01)  # context switch

        # Assert we are sorted in ascending time order.
        timestamp = action_get_timestamp(action)
        assert timestamp >= prev_time, (
            "During history processing the trades/loans are not in ascending order"
        )
        prev_time = timestamp

        if timestamp > end_ts:
            return False, prev_time, count

        self.currently_processing_timestamp = timestamp

        action_type = action_get_type(action)

        try:
            asset1, asset2 = action_get_assets(action)
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found trade with unknown asset {e.asset_name}. '
                f'Ignoring the trade.',
            )
            return True, prev_time, count
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found trade with unsupported asset {e.asset_name}. '
                f'Ignoring the trade.',
            )
            return True, prev_time, count
        except DeserializationError:
            self.msg_aggregator.add_error(
                f'At history processing found trade with non string asset type. '
                f'Ignoring the trade.',
            )
            return True, prev_time, count

        if asset1 in ignored_assets or asset2 in ignored_assets:
            log.debug(
                'Ignoring action with ignored asset',
                action_type=action_type,
                asset1=asset1,
                asset2=asset2,
            )

            return True, prev_time, count

        if action_type == 'loan':
            action = cast(Loan, action)
            self.events.add_loan_gain(
                gained_asset=action.currency,
                lent_amount=action.amount_lent,
                gained_amount=action.earned,
                fee_in_asset=action.fee,
                open_time=action.open_time,
                close_time=timestamp,
            )
            return True, prev_time, count
        elif action_type == 'asset_movement':
            action = cast(AssetMovement, action)
            self.add_asset_movement_to_events(action)
            return True, prev_time, count
        elif action_type == 'margin_position':
            action = cast(MarginPosition, action)
            self.events.add_margin_position(margin=action)
            return True, prev_time, count
        elif action_type == 'ethereum_transaction':
            action = cast(EthereumTransaction, action)
            self.account_for_gas_costs(action)
            return True, prev_time, count

        # if we get here it's a trade
        trade = cast(Trade, action)

        # When you buy, you buy with the cost_currency and receive the other one
        # When you sell, you sell the amount in non-cost_currency and receive
        # costs in cost_currency
        if trade.trade_type == TradeType.BUY:
            self.events.add_buy_and_corresponding_sell(
                bought_asset=trade.base_asset,
                bought_amount=trade.amount,
                paid_with_asset=trade.quote_asset,
                trade_rate=trade.rate,
                fee_in_profit_currency=self.get_fee_in_profit_currency(trade),
                fee_currency=trade.fee_currency,
                timestamp=trade.timestamp,
            )
        elif trade.trade_type == TradeType.SELL:
            self.trade_add_to_sell_events(trade, False)
        elif trade.trade_type == TradeType.SETTLEMENT_SELL:
            # in poloniex settlements sell some asset to get BTC to repay a loan
            self.trade_add_to_sell_events(trade, True)
        elif trade.trade_type == TradeType.SETTLEMENT_BUY:
            # in poloniex settlements you buy some asset with BTC to repay a loan
            # so in essense you sell BTC to repay the loan
            selling_asset = A_BTC
            selling_asset_rate = self.get_rate_in_profit_currency(
                selling_asset,
                trade.timestamp,
            )
            selling_rate = selling_asset_rate * trade.rate
            fee_in_profit_currency = self.get_fee_in_profit_currency(trade)
            gain_in_profit_currency = selling_rate * trade.amount
            # Since the original trade is a buy of some asset with BTC, then the
            # when we invert the sell, the sold amount of BTC should be the cost
            # (amount*rate) of the original buy
            selling_amount = trade.rate * trade.amount
            self.events.add_sell(
                selling_asset=selling_asset,
                selling_amount=selling_amount,
                receiving_asset=None,
                receiving_amount=None,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=fee_in_profit_currency,
                trade_rate=trade.rate,
                rate_in_profit_currency=selling_asset_rate,
                timestamp=trade.timestamp,
                loan_settlement=True,
            )
        else:
            raise ValueError(f'Unknown trade type "{trade.trade_type}" encountered')

        return True, prev_time, count

    def get_calculated_asset_amount(self, asset: Asset) -> Optional[FVal]:
        """Get the amount of asset accounting has calculated we should have after
        the history has been processed
        """
        if asset not in self.events.events:
            return None

        amount = FVal(0)
        for buy_event in self.events.events[asset].buys:
            amount += buy_event.amount
        return amount
