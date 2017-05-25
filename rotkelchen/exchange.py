#!/usr/bin/env python
import json
import os


def data_up_todate(json_data, start_ts, end_ts):
    start_ts_ok = (
        (start_ts is None and json_data['start_time'] is None) or
        start_ts >= json_data['start_time']
    )
    return start_ts_ok and end_ts <= json_data['end_time']


class Exchange(object):

    def __init__(self, name, api_key, secret):
        self.name = name
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False

    def check_trades_cache(self, start_ts, end_ts):
        trades_file = os.path.join(self.data_dir, "%s_trades.json" % self.name)
        trades = dict()
        if os.path.isfile(trades_file):
            with open(trades_file, 'r') as f:
                try:
                    trades = json.loads(f.read())
                except:
                    pass

                # no need to query again
                if data_up_todate(trades, start_ts, end_ts):
                    return trades['data']

        return None

    def update_trades_cache(self, data, start_ts, end_ts):
        trades_file = os.path.join(self.data_dir, "%s_trades.json" % self.name)
        trades = dict()
        with open(trades_file, 'w') as f:
            trades['start_time'] = start_ts
            trades['end_time'] = end_ts
            trades['data'] = data
            f.write(json.dumps(trades))

    def orderBook(self, currency):
        raise NotImplementedError("Should only be implemented by subclasses")

    def set_buy(self, pair, amount, price):
        raise NotImplementedError("Should only be implemented by subclasses")

    def query_balances(self):
        """Returns the balances held in the exchange in the following format:
        {
            'name' : {'amount': 1337, 'usd_value': 42},
            'ICN': {'amount': 42, 'usd_value': 1337}
        }

        The name must be the canonical name used by leftrader
        """
        raise NotImplementedError("Should only be implemented by subclasses")

    def first_connection(self):
        """Performs actions that should be done in the first time coming online
        and attempting to query data from an exchange.
        """
        raise NotImplementedError("Should only be implemented by subclasses")
