import json
import os
import random
from typing import Any, Callable, Dict, List, Optional

from data_faker.utils import assets_exist_at_time

from rotkehlchen.assets.asset import Asset
from rotkehlchen.exchanges.data_structures import Trade, trade_pair_from_assets
from rotkehlchen.exchanges.kraken import kraken_to_world_pair
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import pair_get_assets
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.tests.utils.kraken import create_kraken_trade
from rotkehlchen.typing import Timestamp, TradePair


class FakeKraken():

    def __init__(self) -> None:

        # Use real data from 2019-02-15 for the AssetPairs
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'kraken_asset_pairs.json'), 'r') as f:

            self.asset_pairs = json.loads(f.read())

        # Use real data from 2019-02-23 for the Ticker
        with open(os.path.join(dir_path, 'data', 'kraken_ticker.json'), 'r') as f:

            self.ticker = json.loads(f.read())

        self.trades_dict: Dict[str, Dict[str, Any]] = {}
        self.balances_dict: Dict[str, FVal] = {}
        self.deposits_ledger: List[Dict[str, Any]] = []
        self.withdrawals_ledger: List[Dict[str, Any]] = []
        self.current_ledger_id = 1

    def next_ledger_id(self) -> int:
        ledger_id = self.current_ledger_id
        self.current_ledger_id += 1
        return ledger_id

    def increase_asset(self, asset: Asset, amount: FVal) -> None:
        kraken_asset = asset.to_kraken()
        if kraken_asset not in self.balances_dict:
            self.balances_dict[kraken_asset] = amount
        else:
            self.balances_dict[kraken_asset] += amount

    def decrease_asset(self, asset: Asset, amount: FVal) -> None:
        kraken_asset = asset.to_kraken()
        assert kraken_asset in self.balances_dict, 'Asset should exist in funds'
        msg = 'We should have enough funds to decrease asset'
        assert amount <= self.balances_dict[kraken_asset], msg
        self.balances_dict[kraken_asset] -= amount

    def choose_pair(
            self,
            timestamp: Timestamp,
            price_query: Callable[[Asset, Asset, Timestamp], FVal],
    ) -> TradePair:
        """Choose a random pair to trade from the available pairs at the selected timestamp"""
        choices = set(self.asset_pairs['result'].keys())
        found = False
        while len(choices) != 0:
            pair = random.choice(tuple(choices))
            choices.remove(pair)
            pair = kraken_to_world_pair(pair)
            base, quote = pair_get_assets(pair)
            kbase = base.to_kraken()
            kquote = quote.to_kraken()
            if kbase in self.balances_dict or kquote in self.balances_dict:
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
        kasset = asset.to_kraken()
        return self.balances_dict.get(kasset)

    def deposit(self, asset: Asset, amount: FVal, time: Timestamp) -> None:
        self.increase_asset(asset, amount)
        # and also add it to the ledgers
        entry = {
            'refid': self.next_ledger_id(),
            'time': str(time) + '.0000',
            'type': 'deposit',
            # 'aclass': 'notusedbyrotkehlchen',
            'asset': asset.to_kraken(),
            'amount': str(amount),
            'fee': '0',
            # 'balance': 'notusedbyrotkehlchen',
        }
        self.deposits_ledger.append(entry)

    def append_trade(self, trade: Trade):
        kraken_trade = create_kraken_trade(
            tradeable_pairs=list(self.asset_pairs['result'].keys()),
            pair=trade.pair,
            time=trade.timestamp,
            trade_type=trade.trade_type,
            rate=trade.rate,
            amount=trade.amount,
            fee=trade.fee,
        )
        self.trades_dict[kraken_trade['ordertxid']] = kraken_trade

    # From here and on it's the exchange's API
    def query_asset_pairs(self):
        return self.asset_pairs

    def query_ticker(self):
        return self.ticker

    def query_balances(self):
        response = {'result': self.balances_dict, 'error': []}
        return process_result(response)

    def query_trade_history(self):
        trades_length = len(self.trades_dict)
        response = {'result': {'trades': self.trades_dict, 'count': trades_length}, 'error': []}
        return process_result(response)

    def query_ledgers(self, ledger_type: str):
        if ledger_type == 'all':
            result_list = self.deposits_ledger
            result_list.extend(self.withdrawals_ledger)
            count = len(self.deposits_ledger)
            count += len(self.withdrawals_ledger)
        elif ledger_type == 'deposit':
            count = len(self.deposits_ledger)
            result_list = self.deposits_ledger
        elif ledger_type == 'withdrawal':
            count = len(self.withdrawals_ledger)
            result_list = self.withdrawals_ledger
        else:
            raise ValueError(f'Invalid ledger_type {ledger_type} requested')

        ledger_dict = {}
        for entry in result_list:
            ledger_dict[entry['refid']] = entry
        result = {'ledger': ledger_dict, 'count': count}
        response = {'result': result, 'error': []}
        return process_result(response)
