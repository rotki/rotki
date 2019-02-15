import json
import os


class FakeKraken(object):

    def __init__(self):

        # Use real data from 2019-02-15 for the 2 queried public endpoints
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'kraken_asset_pairs.json'), 'r') as f:

            self.asset_pairs = json.loads(f.read())

        with open(os.path.join(dir_path, 'data', 'kraken_ticker.json'), 'r') as f:

            self.ticker = json.loads(f.read())

    def query_asset_pairs(self):
        return self.asset_pairs

    def query_ticker(self):
        return self.ticker

    # The private endpoints need to be implemented
    def query_trade_volume(self):
        # resp = self.query_private(
        #     'TradeVolume',
        #     req={'pair': 'XETHXXBT', 'fee-info': True},
        # )
        pass

    def query_balances(self):
        # self.query_private('Balance', req={})
        pass

    def query_trade_history(self):
        # result = self.query_until_finished('TradesHistory', 'trades', start_ts, end_ts)
        pass

    def query_ledgers(self):
        # result = self.query_until_finished(
        #     endpoint='Ledgers',
        #     keyname='ledger',
        #     start_ts=start_ts,
        #     end_ts=end_ts,
        #     extra_dict=dict(type='deposit'),
        # )
        # result.extend(self.query_until_finished(
        #     endpoint='Ledgers',
        #     keyname='ledger',
        #     start_ts=start_ts,
        #     end_ts=end_ts,
        #     extra_dict=dict(type='withdrawal'),
        # ))
        pass
