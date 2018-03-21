import time
import hmac
import hashlib
from urllib.parse import urlencode

from rotkehlchen.exchange import Exchange
from rotkehlchen.order_formatting import pair_get_assets, Trade
from rotkehlchen.utils import rlk_jsonloads, cache_response_timewise
from rotkehlchen.fval import FVal

V3_ENDPOINTS = (
    'account',
    'myTrades',
    'openOrders',
)

V1_ENDPOINTS = (
    'exchangeInfo'
)


def binance_pair_to_world(pair):
    return pair[0:3] + '_' + pair[3:]


def trade_from_binance(binance_trade):
    """Turn a binance trade returned from trade history to our common trade
    history format"""
    amount = FVal(binance_trade['qty'])
    rate = FVal(binance_trade['price'])
    pair = binance_pair_to_world(binance_trade['symbol'])

    base_asset, quote_asset = pair_get_assets(pair)

    if binance_trade['isBuyer']:
        order_type = 'buy'
        # e.g. in RDNETH we buy RDN by paying ETH
        cost_currency = quote_asset
    else:
        order_type = 'sell'
        # e.g. in RDNETH we sell RDN to obtain ETH
        cost_currency = base_asset

    fee_currency = binance_trade['commissionAsset']
    fee = FVal(binance_trade['commission'])
    cost = rate * amount

    return Trade(
        timestamp=binance_trade['time'],
        pair=pair,
        type=order_type,
        rate=rate,
        cost=cost,
        cost_currency=cost_currency,
        fee=fee,
        fee_currency=fee_currency,
        amount=amount,
        location='binance'
    )


class Binance(Exchange):
    """Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md

    An unofficial python binance package:
    https://github.com/sammchardy/python-binance
    """
    def __init__(self, api_key, secret, inquirer, data_dir):
        super(Binance, self).__init__('binance', api_key, secret)
        self.apiversion = 'v3'
        self.uri = 'https://api.binance.com/api/'
        self.inquirer = inquirer
        self.data_dir = data_dir
        self.session.headers.update({
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })

    def first_connection(self):
        self.first_connection_made = True

    def validate_api_key(self):
        try:
            self.api_query('account')
        except ValueError as e:
            error = str(e)
            if 'API-key format invalid' in error:
                return False, 'Provided API Key is in invalid Format'
            elif 'Signature for this request is not valid':
                return False, 'Provided API Secret is malformed'
            elif 'Invalid API-key, IP, or permissions for action':
                return 'API Key does not match the given secret'
            else:
                raise
        return True, ''

    def api_query(self, method, options=None):
        if not options:
            options = {}

        with self.lock:
            # Protect this region with a lock since binance will reject
            # non-increasing nonces. So if two greenlets come in here at
            # the same time one of them will fail
            if method in V3_ENDPOINTS:
                api_version = 3
                # Recommended recvWindows is 5000 but we get timeouts with it
                options['recvWindow'] = 10000
                options['timestamp'] = str(int(time.time() * 1000))
                signature = hmac.new(
                    self.secret,
                    urlencode(options).encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                options['signature'] = signature
            elif method in V1_ENDPOINTS:
                api_version = 1
            else:
                raise ValueError('Unexpected binance api method {}'.format(method))

            request_url = self.uri + 'v' + str(api_version) + '/' + method + '?'
            request_url += urlencode(options)

            response = self.session.get(request_url)

        if response.status_code != 200:
            result = rlk_jsonloads(response.text)
            raise ValueError(
                'Binance API request {} for {} failed with HTTP status '
                'code: {}, error code: {} and error message: {}'.format(
                    response.url,
                    method,
                    response.status_code,
                    result['code'],
                    result['msg'],
                ))

        json_ret = rlk_jsonloads(response.text)
        return json_ret

    @cache_response_timewise()
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

    def query_trade_history(self, start_ts=None, end_ts=None, end_at_least_ts=None, markets=None):
        cache = self.check_trades_cache(start_ts, end_at_least_ts)
        if cache is not None:
            return cache

        if not markets:
            markets = []
            exchange_data = self.api_query('exchangeInfo')
            for symbol in exchange_data['symbols']:
                symbol_str = symbol['symbol']
                if isinstance(symbol_str, FVal):
                    symbol_str = str(symbol_str.to_int(exact=True))

                markets.append(symbol_str)

        all_trades_history = list()
        for symbol in markets:
            last_trade_id = 0
            len_result = 500
            while len_result == 500:
                result = self.api_query(
                    'myTrades',
                    options={
                        'symbol': symbol,
                        'fromId': last_trade_id,
                    })
                len_result = len(result)
                for r in result:
                    r['symbol'] = symbol
            all_trades_history.extend(result)

        all_trades_history.sort(key=lambda x: x['time'])

        returned_history = list()
        for order in all_trades_history:
            order_timestamp = int(order['time'] / 1000)
            if start_ts is not None and order_timestamp < start_ts:
                continue
            if end_ts is not None and order_timestamp > end_ts:
                break
            order['time'] = order_timestamp

            returned_history.append(order)

        self.update_trades_cache(returned_history, start_ts, end_ts)
        return returned_history
