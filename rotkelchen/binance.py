import time
import hmac
import hashlib
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

from rotkelchen.exchange import Exchange
from rotkelchen.utils import rlk_jsonloads
from rotkelchen.fval import FVal

V3_ENDPOINTS = (
    'account',
    'myTrades',
)

V1_ENDPOINTS = (
    'exchangeInfo'
)


class Binance(Exchange):
    """Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md
    """
    def __init__(self, api_key, secret, inquirer, data_dir):
        super(Binance, self).__init__('binance', api_key, secret)
        self.apiversion = 'v3'
        self.uri = 'https://api.binance.com/api/'
        self.inquirer = inquirer
        self.data_dir = data_dir

    def api_query(self, method, options=None):
        if not options:
            options = {}

        if method in V3_ENDPOINTS:
            api_version = 3
        elif method in V1_ENDPOINTS:
            api_version = 1
        else:
            raise ValueError('Unexpected binance api method {}'.format(method))

        options['timestamp'] = str(int(time.time() * 1000))
        request_url = self.uri + '/v' + str(api_version) + '/' + method + '?'
        signature = hmac.new(
            self.secret,
            urlencode(options).encode(),
            hashlib.sha256
        ).hexdigest()
        headers = {'X-MBX-APIKEY': self.api_key}
        options['signature'] = signature
        request_url += urlencode(options)
        try:
            ret = urlopen(Request(request_url, headers=headers))
        except HTTPError as e:
            print('Binance API request for {} failed with {} {}'.format(
                method,
                e.code,
                e.msg
            ))
            return {}

        json_ret = rlk_jsonloads(ret.read())
        return json_ret

    def query_balances(self):
        account_data = self.api_query('account')

        returned_balances = dict()
        for entry in account_data['balances']:
            amount = entry['free'] + entry['locked']
            if amount == FVal(0):
                continue
            currency = entry['asset']
            usd_price = self.inquirer.find_usd_price(currency)
            balance = dict()
            balance['amount'] = amount
            balance['usd_value'] = FVal(amount * usd_price)
            returned_balances[currency] = balance

        return returned_balances

    def query_trade_history(self, start_ts=None, end_ts=None, end_at_least_ts=None):
        exchange_data = self.api_query('exchangeInfo')
        symbols = []
        for symbol in exchange_data['symbols']:
            symbols.append(symbol['symbol'])

        #TODO: in progress
        for symbol in symbols:
            pass
