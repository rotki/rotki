import gevent

from rotkehlchen.order_formatting import (
    trade_get_other_pair,
    trade_get_assets,
    Trade,
    AssetMovement
)
from rotkehlchen.transactions import EthereumTransaction
from rotkehlchen.history import FIAT_CURRENCIES
from rotkehlchen.csv_exporter import CSVExporter
from rotkehlchen.fval import FVal
from rotkehlchen.errors import CorruptData

from rotkehlchen.accounting.events import TaxableEvents

import logging
logger = logging.getLogger(__name__)


def action_get_timestamp(action):
    has_timestamp = (
        isinstance(action, Trade) or
        isinstance(action, AssetMovement) or
        isinstance(action, EthereumTransaction)
    )
    if has_timestamp:
        return action.timestamp

    # For loans and manual margin positions
    if 'close_time' not in action:
        print("----> {}".format(action))
    return action['close_time']


def action_get_type(action):
    if isinstance(action, Trade):
        return 'trade'
    elif isinstance(action, AssetMovement):
        return 'asset_movement'
    elif isinstance(action, EthereumTransaction):
        return 'ethereum_transaction'
    elif isinstance(action, dict):
        if 'btc_profit_loss' in action:
            return 'margin_position'
        return 'loan'


def action_get_assets(action):
    if isinstance(action, Trade):
        return trade_get_assets(action)
    elif isinstance(action, AssetMovement):
        return action.asset, None
    elif isinstance(action, EthereumTransaction):
        return 'ETH', None
    elif isinstance(action, dict):
        if 'btc_profit_loss' in action:
            return 'BTC', None

        # else a loan
        return action['currency'], None
    else:
        raise ValueError('Unexpected action type found.')


class Accountant(object):

    def __init__(
            self,
            price_historian,
            profit_currency,
            user_directory,
            create_csv,
            ignored_assets,
            include_crypto2crypto,
    ):

        self.price_historian = price_historian
        self.csvexporter = CSVExporter(profit_currency, user_directory, create_csv)
        self.events = TaxableEvents(price_historian, self.csvexporter, profit_currency)
        self.set_main_currency(profit_currency)

        # Customizable Options
        self.ignored_assets = ignored_assets
        self.events.customize(include_crypto2crypto)

    @property
    def general_trade_pl(self):
        return self.events.general_trade_profit_loss

    @property
    def taxable_trade_pl(self):
        return self.events.taxable_trade_profit_loss

    def set_main_currency(self, currency):
        if currency not in FIAT_CURRENCIES:
            raise ValueError(
                'Attempted to set unsupported "{}" as main currency.'.format(currency)
            )

        self.profit_currency = currency
        self.events.profit_currency = currency

    def query_historical_price(self, from_asset, to_asset, timestamp):
        price = self.price_historian.query_historical_price(from_asset, to_asset, timestamp)
        return price

    def get_rate_in_profit_currency(self, asset, timestamp):
        # TODO: Moved this to events.py too. Is it still needed here?
        if asset == self.profit_currency:
            rate = 1
        else:
            rate = self.query_historical_price(
                asset,
                self.profit_currency,
                timestamp
            )
        assert isinstance(rate, (FVal, int))  # TODO Remove. Is temporary assert
        return rate

    def add_asset_movement_to_events(self, category, asset, amount, timestamp, exchange, fee):
        rate = self.get_rate_in_profit_currency(asset, timestamp)
        self.asset_movement_fees += fee * rate
        if category == 'withdrawal':
            assert fee != 0, "So far all exchanges charge you for withdrawing"

        self.csvexporter.add_asset_movement(
            exchange=exchange,
            category=category,
            asset=asset,
            fee=fee,
            rate=rate,
            timestamp=timestamp,
        )

    def account_for_gas_costs(self, transaction):

        if transaction.gas_price == -1:
            gas_price = self.last_gas_price
        else:
            gas_price = transaction.gas_price
            self.last_gas_price = transaction.gas_price

        rate = self.get_rate_in_profit_currency('ETH', transaction.timestamp)
        eth_burned_as_gas = (transaction.gas_used * gas_price) / FVal(10 ** 18)
        self.eth_transactions_gas_costs += eth_burned_as_gas * rate
        self.csvexporter.add_tx_gas_cost(
            transaction_hash=transaction.hash,
            eth_burned_as_gas=eth_burned_as_gas,
            rate=rate,
            timestamp=transaction.timestamp,
        )

    def trade_add_to_sell_events(self, trade, loan_settlement):
        selling_asset = trade_get_other_pair(trade, trade.cost_currency)
        selling_asset_rate = self.get_rate_in_profit_currency(
            trade.cost_currency,
            trade.timestamp
        )
        selling_rate = selling_asset_rate * trade.rate
        fee_rate = self.query_historical_price(
            trade.fee_currency,
            self.profit_currency,
            trade.timestamp
        )
        total_sell_fee_cost = fee_rate * trade.fee
        gain_in_profit_currency = selling_rate * trade.amount

        if not loan_settlement:
            self.events.add_sell_and_corresponding_buy(
                selling_asset=selling_asset,
                selling_amount=trade.amount,
                receiving_asset=trade.cost_currency,
                receiving_amount=trade.cost,
                gain_in_profit_currency=gain_in_profit_currency,
                total_fee_in_profit_currency=total_sell_fee_cost,
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
                total_fee_in_profit_currency=total_sell_fee_cost,
                trade_rate=trade.rate,
                rate_in_profit_currency=selling_rate,
                timestamp=trade.timestamp,
                loan_settlement=True,
                is_virtual=False
            )

    def process_history(
            self,
            start_ts,
            end_ts,
            trade_history,
            margin_history,
            loan_history,
            asset_movements,
            eth_transactions
    ):
        """Processes the entire history of cryptoworld actions in order to determine
        the price and time at which every asset was obtained and also
        the general and taxable profit/loss.
        """
        self.events.reset(start_ts, end_ts)
        self.last_gas_price = FVal("2000000000")
        self.eth_transactions_gas_costs = FVal(0)
        self.asset_movement_fees = FVal(0)
        self.csvexporter.reset_csv_lists()

        actions = list(trade_history)
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
            key=lambda action: action_get_timestamp(action)
        )

        prev_time = 0
        count = 0
        for action in actions:

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
                break

            action_type = action_get_type(action)

            asset1, asset2 = action_get_assets(action)
            if asset1 in self.ignored_assets or asset2 in self.ignored_assets:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Ignoring {} with {} {}".format(action_type, asset1, asset2))
                    continue

            if action_type == 'loan':
                self.events.add_loan_gain(
                    gained_asset=action['currency'],
                    lent_amount=action['amount_lent'],
                    gained_amount=action['earned'],
                    fee_in_asset=action['fee'],
                    open_time=action['open_time'],
                    close_time=timestamp,
                )
                continue
            elif action_type == 'asset_movement':
                self.add_asset_movement_to_events(
                    category=action.category,
                    asset=action.asset,
                    amount=action.amount,
                    timestamp=action.timestamp,
                    exchange=action.exchange,
                    fee=action.fee
                )
                continue
            elif action_type == 'margin_position':
                self.events.add_margin_position(
                    gained_asset='BTC',
                    gained_amount=action['btc_profit_loss'],
                    fee_in_asset=0,
                    margin_notes=action['notes'],
                    timestamp=timestamp
                )
                continue
            elif action_type == 'ethereum_transaction':
                self.account_for_gas_costs(action)
                continue

            # if we get here it's a trade
            trade = action

            # if the cost is not equal to rate * amount then the data is somehow corrupt
            if not trade.cost.is_close(trade.amount * trade.rate, max_diff="1e-5"):
                raise CorruptData(
                    "Trade found with cost {} which is not equal to trade.amount"
                    "({}) * trade.rate({})".format(trade.cost, trade.amount, trade.rate)
                )

            # When you buy, you buy with the cost_currency and receive the other one
            # When you sell, you sell the amount in non-cost_currency and receive
            # costs in cost_currency
            if trade.type == 'buy':
                self.events.add_buy_and_corresponding_sell(
                    bought_asset=trade_get_other_pair(trade, trade.cost_currency),
                    bought_amount=trade.amount,
                    paid_with_asset=trade.cost_currency,
                    trade_rate=trade.rate,
                    trade_fee=trade.fee,
                    fee_currency=trade.fee_currency,
                    timestamp=trade.timestamp
                )
            elif trade.type == 'sell':
                self.trade_add_to_sell_events(trade, False)
            elif trade.type == 'settlement_sell':
                # in poloniex settlements sell some asset to get BTC to repay a loan
                self.trade_add_to_sell_events(trade, True)
            elif trade.type == 'settlement_buy':
                # in poloniex settlements you buy some asset with BTC to repay a loan
                # so in essense you sell BTC to repay the loan
                selling_asset = 'BTC'
                selling_asset_rate = self.get_rate_in_profit_currency(
                    selling_asset,
                    trade.timestamp
                )
                selling_rate = selling_asset_rate * trade.rate
                fee_rate = self.query_historical_price(
                    trade.fee_currency,
                    self.profit_currency,
                    trade.timestamp
                )
                total_sell_fee_cost = fee_rate * trade.fee
                gain_in_profit_currency = selling_rate * trade.amount
                self.events.add_sell(
                    selling_asset=selling_asset,
                    selling_amount=trade.cost,
                    receiving_asset=None,
                    receiving_amount=None,
                    gain_in_profit_currency=gain_in_profit_currency,
                    total_fee_in_profit_currency=total_sell_fee_cost,
                    trade_rate=trade.rate,
                    rate_in_profit_currency=selling_rate,
                    timestamp=trade.timestamp,
                    loan_settlement=True
                )
            else:
                raise ValueError('Unknown trade type "{}" encountered'.format(trade.type))

        self.events.calculate_asset_details()

        sum_other_actions = (
            self.events.margin_positions_profit +
            self.events.loan_profit -
            self.events.settlement_losses -
            self.asset_movement_fees -
            self.eth_transactions_gas_costs
        )
        total_taxable_pl = self.events.taxable_trade_profit_loss + sum_other_actions
        return {
            'overview': {
                'loan_profit': str(self.events.loan_profit),
                'margin_positions_profit': str(self.events.margin_positions_profit),
                'settlement_losses': str(self.events.settlement_losses),
                'ethereum_transaction_gas_costs': str(self.eth_transactions_gas_costs),
                'asset_movement_fees': str(self.asset_movement_fees),
                'general_trade_profit_loss': str(self.events.general_trade_profit_loss),
                'taxable_trade_profit_loss': str(self.events.taxable_trade_profit_loss),
                'total_taxable_profit_loss': str(total_taxable_pl),
                'total_profit_loss': str(
                    self.events.general_trade_profit_loss +
                    sum_other_actions
                ),
            },
            'all_events': self.csvexporter.all_events,
        }
