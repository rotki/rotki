#!/usr/bin/env python


class Exchange(object):

    def __init__(self, name, api_key, secret):
        self.name = name
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False

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
