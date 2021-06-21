import logging
import random
from typing import Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.assets import A_BTC, A_EUR, A_USD
from rotkehlchen.exchanges.data_structures import Trade, TradeType
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.serialization.deserialize import pair_get_assets
from rotkehlchen.typing import Location, Timestamp, TradePair

STARTING_TIMESTAMP = 1464739200  # 01/06/2016
NUMBER_OF_TRADES = 5
STARTING_FUNDS = {A_EUR: FVal(100000), A_BTC: FVal(10)}

MAX_TRADE_DIFF_VARIANCE = 14400

ALLOWED_EXCHANGES = ['kraken', 'binance']
KRAKEN_PAIRS = [TradePair('ETH_EUR'), TradePair('BTC_EUR')]

MAX_TRADE_USD_VALUE = FVal(100)
MAX_FEE_USD_VALUE = 1


logger = logging.getLogger(__name__)


class ActionWriter():

    def __init__(
            self,
            trades_number: int,
            seconds_between_trades: int,
            seconds_between_balance_save: int,
            rotkehlchen,
            fake_kraken,
            fake_binance,
    ):
        self.seconds_between_trades = seconds_between_trades
        self.seconds_between_balance_save = seconds_between_balance_save
        self.trades_number = trades_number
        self.current_ts = STARTING_TIMESTAMP
        self.last_trade_ts = 0
        self.last_balance_save_ts = 0
        self.funds = STARTING_FUNDS
        self.rotki = rotkehlchen
        self.kraken = fake_kraken
        self.binance = fake_binance

        timestamp, _, _ = self.get_next_ts()
        for asset, value in self.funds.items():
            if asset.is_fiat():
                self.rotki.data.db.add_manually_tracked_balances([ManuallyTrackedBalance(
                    asset=asset,
                    label=f'{asset.identifier} balance',
                    amount=value,
                    location=Location.BANKS,
                    tags=None,
                )])
        self.rotki.query_balances(requested_save_data=True, timestamp=timestamp)

        # divide our starting funds between exchanges and keep a part out
        divide_by = len(ALLOWED_EXCHANGES) + 1
        for asset, value in self.funds.items():
            amount = value / divide_by
            for exchange in ALLOWED_EXCHANGES:
                timestamp, _, _ = self.get_next_ts()

                skip_exchange = asset.is_fiat() and exchange != 'kraken'

                if not skip_exchange:
                    getattr(self, exchange).deposit(
                        asset=asset,
                        amount=amount,
                        time=timestamp,
                    )
                if asset.is_fiat():
                    self.rotki.data.db.add_manually_tracked_balances([ManuallyTrackedBalance(
                        asset=asset,
                        label=f'{asset.identifier} balance {timestamp}',
                        amount=value,
                        location=Location.BANKS,
                        tags=None,
                    )])

        self.rotki.query_balances(requested_save_data=True, timestamp=timestamp)
        self.last_balance_save_ts = timestamp

    def maybe_save_balances(self, save_ts: Timestamp) -> None:
        """Maybe Save all current balances in the fake user's DB at the current timestamp

        If the save_ts is not after the time we save balances then nothing happens
        """
        if save_ts - self.last_balance_save_ts < self.seconds_between_balance_save:
            return
        self.rotki.query_balances(requested_save_data=True, timestamp=save_ts)
        self.last_balance_save_ts = save_ts

    def generate_history(self) -> None:
        created_trades = 0
        while created_trades <= self.trades_number:
            current_ts, save_balances, make_trade = self.get_next_ts()

            if make_trade:
                try:
                    self.create_action(created_trades, current_ts)
                    created_trades += 1
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(f'failed to create trade: {e}')

            if save_balances:
                self.maybe_save_balances(save_ts=current_ts)

    @staticmethod
    def query_historical_price(from_asset: Asset, to_asset: Asset, timestamp: Timestamp):
        return PriceHistorian().query_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

    def increase_asset(self, asset: Asset, amount: FVal, exchange: str) -> None:
        if asset not in self.funds:
            self.funds[asset] = amount
        else:
            self.funds[asset] += amount

        getattr(self, exchange).increase_asset(asset, amount)

    def decrease_asset(self, asset: Asset, amount: FVal, exchange: str) -> None:
        assert asset in self.funds, 'Asset should exist in funds'
        assert amount <= self.funds[asset], 'We should have enough funds to decrease asset'
        self.funds[asset] -= amount

        getattr(self, exchange).decrease_asset(asset, amount)

    def get_next_ts(self) -> Tuple[Timestamp, bool, bool]:
        current_ts = self.current_ts
        advance_by_secs = min(self.seconds_between_trades, self.seconds_between_balance_save)
        secs_in_future = random.randint(
            advance_by_secs,
            advance_by_secs + MAX_TRADE_DIFF_VARIANCE,
        )
        self.current_ts += secs_in_future

        save_balances = False
        if self.current_ts - self.last_balance_save_ts >= self.seconds_between_balance_save:
            save_balances = True

        make_trade = False
        if self.current_ts - self.last_trade_ts >= self.seconds_between_trades:
            make_trade = True

        return Timestamp(current_ts), save_balances, make_trade

    def create_action(self, index: int, ts: Timestamp):
        """Create a random trade action on a random exchange depending
        on the funds that are available in that exchange"""
        # choose an exchange at random
        exchange_name = random.choice(ALLOWED_EXCHANGES)
        exchange = getattr(self, exchange_name)
        # choose a random pair at that exchange
        pair = exchange.choose_pair(
            timestamp=ts,
            price_query=self.query_historical_price,
        )
        print(
            f'Creating trade {index + 1} / {self.trades_number} in {exchange_name}'
            f' for the pair: {pair} at timestamp {ts}',
        )
        # depending on our funds decide on what to do. Buy/sell
        base, quote = pair_get_assets(pair)
        if exchange.get_balance(base) is None:
            action_type = TradeType.BUY
        elif exchange.get_balance(quote) is None:
            action_type = TradeType.SELL
        else:
            # TODO: trade the one we have most of
            action_type = random.choice(list(TradeType))

        # if we are buying we are going to spend from the quote asset
        if action_type == TradeType.BUY:
            spending_asset = quote
        else:  # selling spends from the base asset
            spending_asset = base
        # get a spending asset amount within our per-trade equivalent range and
        # our available funds
        spending_usd_rate = self.query_historical_price(spending_asset, A_USD, ts)
        max_usd_in_spending_asset = spending_usd_rate * exchange.get_balance(spending_asset)
        max_usd_equivalent_to_spend = min(max_usd_in_spending_asset, MAX_TRADE_USD_VALUE)
        rate = self.query_historical_price(base, quote, ts)
        usd_to_spend = FVal(random.uniform(0.01, float(max_usd_equivalent_to_spend)))
        amount_in_spending_asset = usd_to_spend / spending_usd_rate
        # if we are buying then the amount is the amount of asset we bought
        if action_type == TradeType.BUY:
            amount = amount_in_spending_asset / rate
        # if we are selling the amount is the spending asset amount
        else:
            amount = amount_in_spending_asset

        quote_asset_usd_rate = self.query_historical_price(quote, A_USD, ts)
        fee_in_quote_currency = FVal(random.uniform(0, MAX_FEE_USD_VALUE)) / quote_asset_usd_rate

        # create the trade
        base, quote = pair.split('_')
        trade = Trade(
            timestamp=ts,
            location=Location.deserialize(exchange_name),
            base_asset=base,
            quote_asset=quote,
            trade_type=action_type,
            amount=amount,
            rate=rate,
            fee=fee_in_quote_currency,
            fee_currency=quote,
            link='',
            notes='',
        )
        logger.info(f'Created trade: {trade}')

        # Adjust our global and per exchange accounting
        if action_type == TradeType.BUY:
            # we buy so we increase our base asset by amount
            self.increase_asset(base, amount, exchange_name)
            # and decrease quote by amount * rate
            self.decrease_asset(quote, amount * rate, exchange_name)
        else:
            # we sell so we increase our quote asset
            self.increase_asset(quote, amount * rate, exchange_name)
            # and decrease our base asset
            self.decrease_asset(base, amount, exchange_name)

        # finally add it to the exchange
        exchange.append_trade(trade)
