import logging
import random

from rotkehlchen.constants import FIAT_CURRENCIES
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import Trade, pair_get_assets
from rotkehlchen.typing import Asset, Timestamp

STARTING_TIMESTAMP = 1464739200  # 01/06/2016
NUMBER_OF_TRADES = 5
STARTING_FUNDS = {'EUR': FVal(100000)}

MIN_SECONDS_BETWEEN_TRADES = 86400
MAX_TRADE_DIFF_VARIANCE = 14400

ALLOWED_EXCHANGES = ['kraken']
KRAKEN_PAIRS = ['ETH_EUR', 'BTC_EUR']

ALLOWED_ASSETS = ['ETH', 'BTC']

MAX_TRADE_USD_VALUE = FVal(100)
MAX_FEE_USD_VALUE = 1

MIN_DIFF_BETWEEN_BALANCE_SAVING = 172800


logger = logging.getLogger(__name__)


class ActionWriter(object):

    def __init__(self, trades_number, rotkehlchen, fake_kraken):
        self.trades_number = trades_number
        self.current_ts = STARTING_TIMESTAMP
        self.last_balance_save_ts = 0
        self.funds = STARTING_FUNDS
        self.rotki = rotkehlchen
        self.fake_kraken = fake_kraken

        timestamp = self.get_next_ts()
        for asset, value in self.funds.items():
            if asset in FIAT_CURRENCIES:
                self.rotki.data.db.add_fiat_balance(asset, value)
        self.rotki.query_balances(requested_save_data=True, timestamp=timestamp)

        timestamp = self.get_next_ts()
        # for now since we only got kraken, deposit half of our starting funds to it
        for asset, value in self.funds.items():
            amount = value / 2
            self.fake_kraken.deposit(
                asset=asset,
                amount=amount,
                time=timestamp,
            )
            self.rotki.data.db.add_fiat_balance(asset, amount)
        self.rotki.query_balances(requested_save_data=True, timestamp=timestamp)
        self.last_balance_save_ts = timestamp

    def maybe_save_balances(self, save_ts: Timestamp) -> None:
        """Maybe Save all current balances in the fake user's DB at the current timestamp

        If the save_ts is not after MIN_DIFF_BETWEEN_BALANCE_SAVING then nothing happens
"""
        if save_ts - self.last_balance_save_ts < MIN_DIFF_BETWEEN_BALANCE_SAVING:
            return
        self.rotki.query_balances(requested_save_data=True, timestamp=save_ts)
        self.last_balance_save_ts = save_ts

    def generate_history(self):
        for _ in range(0, self.trades_number):
            self.create_action()

    def query_historical_price(self, from_asset, to_asset, timestamp):
        return self.rotki.accountant.price_historian.query_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

    def increase_asset(self, asset: Asset, amount: FVal, exchange='kraken') -> None:
        if asset not in self.funds:
            self.funds[asset] = amount
        else:
            self.funds[asset] += amount

        # TODO: here should select based on exchange
        self.fake_kraken.increase_asset(asset, amount)

    def decrease_asset(self, asset: Asset, amount: FVal, exchange='kraken') -> None:
        assert asset in self.funds, 'Asset should exist in funds'
        assert amount <= self.funds[asset], 'We should have enough funds to decrease asset'
        self.funds[asset] -= amount
        # TODO: here should select based on exchange
        self.fake_kraken.decrease_asset(asset, amount)

    def get_next_ts(self):
        current_ts = self.current_ts
        secs_in_future = random.randint(
            MIN_SECONDS_BETWEEN_TRADES,
            MIN_SECONDS_BETWEEN_TRADES + MAX_TRADE_DIFF_VARIANCE,
        )
        self.current_ts += secs_in_future
        return current_ts

    def choose_pair(self):
        choices = set(KRAKEN_PAIRS)
        found = False
        while len(choices) != 0:
            pair = random.choice(tuple(choices))
            choices.remove(pair)
            base, quote = pair_get_assets(pair)
            if base in self.funds or quote in self.funds:
                found = True
                break

        if not found:
            raise ValueError('Could not find a pair to trade with the current funds')

        return pair

    def create_action(self):
        """Create a random trade action"""
        ts = self.get_next_ts()
        # choose a random pair
        pair = self.choose_pair()
        # depending on our funds decide on what to do. Buy/sell
        base, quote = pair_get_assets(pair)
        if base not in self.funds:
            action_type = 'buy'
        elif quote not in self.funds:
            action_type = 'sell'
        else:
            # TODO: trade the one we have most of
            action_type = random.choice(('buy', 'sell'))

        # if we are buying we are going to spend from the quote asset
        if action_type == 'buy':
            spending_asset = quote
        else:  # selling spends from the base asset
            spending_asset = base
        # get a spending asset amount within our per-trade equivalent range and
        # our available funds
        spending_usd_rate = self.query_historical_price(spending_asset, 'USD', ts)
        max_usd_in_spending_asset = spending_usd_rate * self.funds[spending_asset]
        max_usd_equivalent_to_spend = min(max_usd_in_spending_asset, MAX_TRADE_USD_VALUE)
        rate = self.query_historical_price(base, quote, ts)
        usd_to_spend = FVal(random.uniform(0.01, float(max_usd_equivalent_to_spend)))
        amount_in_spending_asset = usd_to_spend / spending_usd_rate
        # if we are buying then the amount of asset we bought
        if action_type == 'buy':
            amount = amount_in_spending_asset / rate
        # if we are selling the amount is the spending asset amount
        else:
            amount = amount_in_spending_asset

        quote_asset_usd_rate = self.query_historical_price(base, quote, ts)
        fee_in_quote_currency = FVal(random.uniform(0, MAX_FEE_USD_VALUE)) / quote_asset_usd_rate

        # create the trade
        trade = Trade(
            timestamp=ts,
            location='kraken',
            pair=pair,
            trade_type=action_type,
            amount=amount,
            rate=rate,
            fee=fee_in_quote_currency,
            fee_currency=quote,
            link='',
            notes='',
        )

        logger.info(f'Created trade: {trade}')

        if action_type == 'buy':
            # we buy so we increase our base asset by amount
            self.increase_asset(base, amount)
            # and decrease quote by amount * rate
            self.decrease_asset(quote, amount * rate)
        else:
            # we sell so we increase our quote asset
            self.increase_asset(quote, amount * rate)
            # and decrease our base asset
            self.decrease_asset(base, amount)

        # normally here you would input it into the appropriate fake exchange
        # but since we only got kraken faker now ...
        self.fake_kraken.append_trade(trade)

        self.maybe_save_balances(save_ts=ts)
