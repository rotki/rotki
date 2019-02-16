import json
import os

from rotkehlchen.fval import FVal
from rotkehlchen.kraken import WORLD_TO_KRAKEN
from rotkehlchen.tests.fixtures.exchanges.kraken import create_kraken_trade
from rotkehlchen.typing import Asset, Timestamp, Trade
from rotkehlchen.utils import process_result


class FakeKraken(object):

    def __init__(self):

        # Use real data from 2019-02-15 for the 2 queried public endpoints
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'kraken_asset_pairs.json'), 'r') as f:

            self.asset_pairs = json.loads(f.read())

        with open(os.path.join(dir_path, 'data', 'kraken_ticker.json'), 'r') as f:

            self.ticker = json.loads(f.read())

        self.trades_dict = {}
        self.balances_dict = {}
        self.deposits_ledger = []
        self.withdrawals_ledger = []

    def increase_asset(self, asset: Asset, amount: FVal) -> None:
        asset = WORLD_TO_KRAKEN[asset]
        if asset not in self.balances_dict:
            self.balances_dict[asset] = amount
        else:
            self.balances_dict[asset] += amount

    def decrease_asset(self, asset: Asset, amount: FVal) -> None:
        asset = WORLD_TO_KRAKEN[asset]
        assert asset in self.balances_dict, 'Asset should exist in funds'
        assert amount <= self.balances_dict[asset], 'We should have enough funds to decrease asset'
        self.balances_dict[asset] -= amount

    def deposit(self, asset: Asset, amount: FVal, time: Timestamp) -> None:
        self.increase_asset(asset, amount)
        # and also add it to the ledgers
        entry = {
            # 'refid': 'notusedbyrotkehlchen',
            'time': str(time) + '.0000',
            'type': 'deposit',
            # 'aclass': 'notusedbyrotkehlchen',
            'asset': WORLD_TO_KRAKEN[asset],
            'amount': str(amount),
            'fee': '0',
            # 'balance': 'notusedbyrotkehlchen',
        }
        self.deposits_ledger.append(entry)

    def append_trade(self, trade: Trade):
        kraken_trade = create_kraken_trade(
            tradeable_pairs=list(self.asset_pairs['result'].keys()),
            pair=trade.pair,
            time=trade.time,
            trade_type=trade.trade_type,
            rate=trade.rate,
            amount=trade.amount,
            fee=trade.fee,
        )
        self.trades_dict[kraken_trade['ordertxid']] = kraken_trade

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
        elif ledger_type == 'deposit':
            result_list = self.deposits_ledger
        elif ledger_type == 'withdrawal':
            result_list = self.withdrawals_ledger
        else:
            raise ValueError(f'Invalid ledger_type {ledger_type} requested')

        response = {'result': result_list, 'error': []}
        return process_result(response)
