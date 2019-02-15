import logging
import random

from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import pair_get_assets
from rotkehlchen.typing import Asset, Trade

STARTING_TIMESTAMP = 1464739200  # 01/06/2016
NUMBER_OF_TRADES = 5
STARTING_FUNDS = {'EUR': FVal(10000)}

MIN_SECONDS_BETWEEN_TRADES = 86400
MAX_TRADE_DIFF_VARIANCE = 14400

ALLOWED_EXCHANGES = ['kraken']
KRAKEN_PAIRS = ['ETH_EUR', 'BTC_EUR']

ALLOWED_ASSETS = ['ETH', 'BTC']

MAX_TRADE_USD_VALUE = 100
MAX_FEE_USD_VALUE = 1


logger = logging.getLogger(__name__)


class ActionWriter(object):

    def __init__(self, rotkehlchen, fake_kraken):
        self.current_ts = STARTING_TIMESTAMP
        self.funds = STARTING_FUNDS
        self.rotki = rotkehlchen
        self.fake_kraken = fake_kraken

    def do():
        pass

    def query_historical_price(self, from_asset, to_asset, timestamp):
        return self.rotki.accountant.price_historian.query_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

    def increase_asset(self, asset: Asset, amount: FVal) -> None:
        if asset not in self.funds:
            self.funds[asset] = amount
        else:
            self.funds[asset] += amount

    def decrease_asset(self, asset: Asset, amount: FVal) -> None:
        assert asset in self.funds, 'Asset should exist in funds'
        assert amount <= self.funds[asset], 'We should have enough funds to decrease asset'
        self.funds[asset] -= amount

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
            asset = quote
        else:  # selling spends from the base asset
            asset = base
        # get a spending asset amount within our per-trade equivalent range
        usd_rate = self.query_historical_price(asset, 'USD', ts)
        rate = self.query_historical_price(base, quote, ts)
        amount = FVal(random.uniform(0.01, MAX_TRADE_USD_VALUE)) / usd_rate

        quote_asset_usd_rate = self.query_historical_price(base, quote, ts)
        fee_in_quote_currency = FVal(random.uniform(0, MAX_FEE_USD_VALUE)) / quote_asset_usd_rate

        # create the trade
        trade = Trade(
            time=ts,
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
