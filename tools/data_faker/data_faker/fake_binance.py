import json
import os
import random
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from data_faker.utils import assets_exist_at_time

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.exchanges.binance import create_binance_symbols_to_pair
from rotkehlchen.exchanges.data_structures import Trade, TradeType, trade_pair_from_assets
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import pair_get_assets
from rotkehlchen.serialization.serialize import process_result, process_result_list
from rotkehlchen.typing import Timestamp, TradePair

# Disallow some assets for simplicity
DISALLOWED_ASSETS = (
    # BCC is Bitcoin Cash and known as BCH to Rotkehlchen. Also has 2 other forks
    # BCHABC and BCHSV
    'BCC',
    'BCHSV',
    'BCHABC',
    # https://support.binance.com/hc/en-us/articles/360007439672-Information-Regarding-the-Upcoming-VEN-VET-Mainnet-Swap
    'VEN',
    'VET',
    # This "red pulse" does not seem to be traded anymore
    'RPX',
    # For some timestamps BTC to USDT does not work in cryptocompare while
    # USDT to USD does. This is rather strange ... and probably would need
    # some code adjustments to make it work for cryptocompare
    # rotkehlchen.history.NoPriceForGivenTimestamp: Unable to query a historical
    # price for "BTC" to "USDT" at 17/06/2016, 00:18:04
    'USDT',
)


class FakeBinance():

    def __init__(self) -> None:
        this_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = Path(this_dir).parent.parent.parent
        json_path = (
            root_dir / 'rotkehlchen' / 'tests' / 'utils' / 'data' / 'binance_exchange_info.json'
        )
        with json_path.open('r') as f:
            self._exchange_info = json.loads(f.read())

        self._symbols_to_pair = create_binance_symbols_to_pair(self._exchange_info)

        self.trades_list: List[Dict[str, Any]] = []
        self.balances_dict: Dict[str, FVal] = {}
        self.deposits_ledger: List[Dict[str, Any]] = []
        self.withdrawals_ledger: List[Dict[str, Any]] = []

    def increase_asset(self, asset: Asset, amount: FVal) -> None:
        binance_symbol = asset.to_binance()
        if binance_symbol not in self.balances_dict:
            self.balances_dict[binance_symbol] = amount
        else:
            self.balances_dict[binance_symbol] += amount

    def decrease_asset(self, asset: Asset, amount: FVal) -> None:
        binance_symbol = asset.to_binance()
        assert binance_symbol in self.balances_dict, 'Asset should exist in funds'
        msg = 'We should have enough funds to decrease asset'
        assert amount <= self.balances_dict[binance_symbol], msg
        self.balances_dict[binance_symbol] -= amount

    def choose_pair(
            self,
            timestamp: Timestamp,
            price_query: Callable[[Asset, Asset, Timestamp], FVal],
    ) -> TradePair:
        """Choose a random pair to trade from the available pairs at the selected timestamp"""
        choices = set(self._symbols_to_pair.keys())
        found = False
        while len(choices) != 0:
            pair = random.choice(tuple(choices))
            choices.remove(pair)
            binance_pair = self._symbols_to_pair[pair]
            bbase = binance_pair.binance_base_asset
            bquote = binance_pair.binance_quote_asset
            try:
                base = asset_from_binance(bbase)
                quote = asset_from_binance(bquote)
            except UnsupportedAsset:
                continue

            if bbase in self.balances_dict or bquote in self.balances_dict:
                if bbase in DISALLOWED_ASSETS or bquote in DISALLOWED_ASSETS:
                    continue

                # Before choosing make sure that at the selected timestamp both of
                # the pair assets exist (had a price)
                if not assets_exist_at_time(base, quote, timestamp, price_query):
                    continue

                found = True
                break

        if not found:
            raise ValueError('Could not find a pair to trade with the current funds')
        return trade_pair_from_assets(base, quote)

    def get_balance(self, asset: Asset) -> Optional[FVal]:
        """Returns the balance of asset that's held in the exchance or None"""
        return self.balances_dict.get(asset.identifier)

    def deposit(
            self,
            asset: Asset,
            amount: FVal,
            time: Timestamp,  # pylint: disable=unused-argument
    ) -> None:
        self.increase_asset(asset, amount)

    def append_trade(self, trade: Trade):
        trade_data = self.trade_to_binance(trade)
        self.trades_list.append(trade_data)

    def trade_to_binance(self, trade: Trade) -> Dict[str, Any]:
        """Turns our trade into a binance trade"""
        base, quote = pair_get_assets(trade.pair)
        bbase = base.to_binance()
        bquote = quote.to_binance()
        binance_symbol = bbase + bquote
        # Binance trades have timestamps with 3 extra zeros at the end
        timestamp = trade.timestamp * 1000
        msg = 'The given trade symbol is not a valid binance pair'
        assert binance_symbol in self._symbols_to_pair, msg

        trade_data = {
            'symbol': binance_symbol,
            'id': 1,
            'orderId': 1,
            'price': str(trade.rate),
            'qty': str(trade.amount),
            'commission': str(trade.fee),
            'commissionAsset': str(trade.fee_currency.to_binance()),
            'time': timestamp,
            'isBuyer': trade.trade_type == TradeType.BUY,
            'isMaker': True,
            'isBestMatch': True,
        }
        return trade_data

    # From here and on it's the exchange's API
    def query_exchange_info(self):
        return self._exchange_info

    def query_account(self):
        result_data = {
            'makerCommission': 15,
            'takerCommission': 15,
            'buyerCommission': 0,
            'sellerCommission': 0,
            'canTrade': True,
            'canWithdraw': True,
            'canDeposit': True,
            'updateTime': 123456789,
        }
        balances = []
        for asset, value in self.balances_dict.items():
            balances.append({
                'asset': asset,
                'free': str(value),
                'locked': '0.0',
            })
        result_data['balances'] = balances
        return process_result(result_data)

    def query_my_trades(self, symbol):
        # Ignore all other options and just use the symbol
        result = []
        for trade in self.trades_list:
            if trade['symbol'] == symbol:
                result.append(trade)

        return process_result_list(result)
