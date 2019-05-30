import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import gevent

from rotkehlchen.accounting.events import TaxableEvents
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.errors import PriceQueryUnknownFromAsset, UnknownAsset, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.order_formatting import (
    AssetMovement,
    MarginPosition,
    Trade,
    TradeType,
    trade_get_assets,
)
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.typing import Fee, FilePath, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TaxableAction = Union[Trade, AssetMovement, EthereumTransaction, MarginPosition, Dict]


def action_get_timestamp(action: TaxableAction) -> Timestamp:
    has_timestamp = (
        isinstance(action, Trade) or
        isinstance(action, AssetMovement) or
        isinstance(action, EthereumTransaction)
    )
    if has_timestamp:
        return action.timestamp  # type: ignore # There is an isinstance check above

    if isinstance(action, MarginPosition):
        return action.close_time

    # For loans
    assert isinstance(action, Dict) and 'close_time' in action, (
        'Unexpected action in get_timestamp'
    )
    return action['close_time']


def action_get_type(action: TaxableAction) -> str:
    if isinstance(action, Trade):
        return 'trade'
    elif isinstance(action, AssetMovement):
        return 'asset_movement'
    elif isinstance(action, EthereumTransaction):
        return 'ethereum_transaction'
    elif isinstance(action, MarginPosition):
        return 'margin_position'
    elif isinstance(action, dict):
        return 'loan'

    raise ValueError('Unexpected action type found.')


def action_get_assets(
        action: TaxableAction,
) -> Tuple[Asset, Optional[Asset]]:
    if isinstance(action, Trade):
        return trade_get_assets(action)
    elif isinstance(action, AssetMovement):
        return action.asset, None
    elif isinstance(action, EthereumTransaction):
        return A_ETH, None
    elif isinstance(action, MarginPosition):
        return action.pl_currency, None
    elif isinstance(action, dict):
        # else a loan
        return action['currency'], None

    else:
        raise ValueError('Unexpected action type found.')


class Accountant():

    def __init__(
            self,
            profit_currency: Asset,
            user_directory: FilePath,
            msg_aggregator: MessagesAggregator,
            create_csv: bool,
            ignored_assets: List[Asset],
            include_crypto2crypto: bool,
            taxfree_after_period: int,
            include_gas_costs: bool,
    ):
        self.msg_aggregator = msg_aggregator
        self.csvexporter = CSVExporter(profit_currency, user_directory, create_csv)
        self.events = TaxableEvents(self.csvexporter, profit_currency)
        self.set_main_currency(profit_currency.identifier)

        self.asset_movement_fees = FVal(0)
        self.last_gas_price = FVal(0)

        self.currently_processed_timestamp = -1

        # Customizable Options
        self.ignored_assets = ignored_assets
        self.include_gas_costs = include_gas_costs
        self.events.include_crypto2crypto = include_crypto2crypto
        self.events.taxfree_after_period = taxfree_after_period

    def __del__(self):
        del self.events
        del self.csvexporter

    @property
    def general_trade_pl(self) -> FVal:
        return self.events.general_trade_profit_loss

    @property
    def taxable_trade_pl(self) -> FVal:
        return self.events.taxable_trade_profit_loss

    def customize(self, settings: Dict[str, Any]) -> Tuple[bool, str]:
        include_c2c = self.events.include_crypto2crypto
        taxfree_after_period = self.events.taxfree_after_period

        if 'include_crypto2crypto' in settings:
            include_c2c = settings['include_crypto2crypto']
            if not isinstance(include_c2c, bool):
                return False, 'Value for include_crypto2crypto must be boolean'

        if 'taxfree_after_period' in settings:
            taxfree_after_period = settings['taxfree_after_period']
            if taxfree_after_period is not None:
                if not isinstance(taxfree_after_period, int):
                    return False, 'Value for taxfree_after_period must be an integer'

                if taxfree_after_period == 0:
                    return False, 'Value for taxfree_after_period can not be 0 days'

                # turn to seconds
                taxfree_after_period = taxfree_after_period * 86400
                settings['taxfree_after_period'] = taxfree_after_period

        self.events.include_crypto2crypto = include_c2c
        self.events.taxfree_after_period = taxfree_after_period

        return True, ''

    def set_main_currency(self, given_currency: str) -> None:
        currency = Asset(given_currency)
        msg = 'main currency checks should have happened at rotkehlchen.set_settings()'
        assert currency.is_fiat(), msg

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
            trade.fee_currency,
            self.profit_currency,
            trade.timestamp,
        )
        return fee_rate * trade.fee

    def add_asset_movement_to_events(
            self,
            category: str,
            asset: Asset,
            timestamp: Timestamp,
            exchange: str,
            fee: Fee,
    ) -> None:
        if timestamp < self.start_ts:
            return

        rate = self.get_rate_in_profit_currency(asset, timestamp)
        cost = fee * rate
        self.asset_movement_fees += cost
        log.debug(
            'Accounting for asset movement',
            sensitive_log=True,
            category=category,
            asset=asset,
            cost_in_profit_currency=cost,
            timestamp=timestamp,
            exchange_name=exchange,
        )
        if category == 'withdrawal':
            assert fee != 0, 'So far all exchanges charge you for withdrawing'

        self.csvexporter.add_asset_movement(
            exchange=exchange,
            category=category,
            asset=asset,
            fee=fee,
            rate=rate,
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
            transaction_hash=transaction.hash,
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
            trade_history: List[Trade],
            margin_history: List[Trade],
            loan_history: Dict,
            asset_movements: List[AssetMovement],
            eth_transactions: List[EthereumTransaction],
    ) -> Dict[str, Any]:
        """Processes the entire history of cryptoworld actions in order to determine
        the price and time at which every asset was obtained and also
        the general and taxable profit/loss.
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
        self.currently_processed_timestamp = start_ts

        actions: List[TaxableAction] = list(trade_history)
        # If we got loans, we need to interleave them with the full history and re-sort
        if len(loan_history) != 0:
            actions.extend(loan_history)

        if len(asset_movements) != 0:
            actions.extend(asset_movements)

        if len(margin_history) != 0:
            actions.extend(margin_history)

        if len(eth_transactions) != 0:
            actions.extend(eth_transactions)

        actions.sort(
            key=lambda action: action_get_timestamp(action),
        )

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
                log.error(f'Skipping trade during history processing: {str(e)}')
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
        # the losing remote after hearbeat error for the zerorpc client.
        # https://github.com/0rpc/zerorpc-python/issues/37
        # TODO: Find better way to do this. Perhaps enforce this only if method
        # is a synced call, and if async don't do this yielding. In any case
        # this calculation should definitely by async
        count += 1
        if count % 500 == 0:
            gevent.sleep(0.01)  # context switch

        # Assert we are sorted in ascending time order.
        timestamp = action_get_timestamp(action)
        assert timestamp >= prev_time, (
            "During history processing the trades/loans are not in ascending order"
        )
        prev_time = timestamp

        if timestamp > end_ts:
            return False, prev_time, count

        self.currently_processed_timestamp = timestamp

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
        if asset1 in self.ignored_assets or asset2 in self.ignored_assets:
            log.debug(
                'Ignoring action with ignored asset',
                action_type=action_type,
                asset1=asset1,
                asset2=asset2,
            )

            return True, prev_time, count

        if action_type == 'loan':
            action = cast(Dict, action)
            self.events.add_loan_gain(
                gained_asset=action['currency'],
                lent_amount=action['amount_lent'],
                gained_amount=action['earned'],
                fee_in_asset=action['fee'],
                open_time=action['open_time'],
                close_time=timestamp,
            )
            return True, prev_time, count
        elif action_type == 'asset_movement':
            action = cast(AssetMovement, action)
            self.add_asset_movement_to_events(
                category=action.category,
                asset=action.asset,
                timestamp=action.timestamp,
                exchange=action.exchange,
                fee=action.fee,
            )
            return True, prev_time, count
        elif action_type == 'margin_position':
            action = cast(MarginPosition, action)
            self.events.add_margin_position(
                gain_loss_asset=action.pl_currency,
                gain_loss_amount=action.profit_loss,
                fee_in_asset=Fee(ZERO),
                margin_notes=action.notes,
                timestamp=action.close_time,
            )
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
