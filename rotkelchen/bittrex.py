import time
import hmac
import urllib
import urllib2
import hashlib
import json

from utils import createTimeStamp, ts_now, get_pair_position
from exchange import Exchange
from order_formatting import Trade


BITTREX_MARKET_METHODS = {
    'getopenorders',
    'cancel',
    'sellmarket',
    'selllimit',
    'buymarket',
    'buylimit'
}
BITTREX_ACCOUNT_METHODS = {
    'getbalances',
    'getbalance',
    'getdepositaddress',
    'withdraw',
    'getorderhistory'
}


def bittrex_pair_to_world(pair):
    return pair.replace('-', '_')


def world_pair_to_bittrex(pair):
    return pair.replace('_', '-')


def trade_from_bittrex(bittrex_trade):
    """Turn a bittrex trade returned from bittrex trade history to our common trade
    history format"""
    amount = float(bittrex_trade['Quantity']) - float(bittrex_trade['QuantityRemaining'])
    rate = float(bittrex_trade['PricePerUnit'])
    order_type = bittrex_trade['OrderType']
    bittrex_price = float(bittrex_trade['Price'])
    bittrex_commission = float(bittrex_trade['Commission'])
    pair = bittrex_pair_to_world(bittrex_trade['Exchange'])
    base_currency = get_pair_position(pair, 'first')
    if order_type == 'LIMIT_BUY':
        order_type = 'buy'
        cost = bittrex_price + bittrex_commission
        fee = bittrex_commission
    elif order_type == 'LIMIT_SEL':
        order_type = 'sell'
        cost = bittrex_price - bittrex_commission
        fee = bittrex_commission
    else:
        raise ValueError('Got unexpected order type "{}" for bittrex trade'.format(order_type))

    return Trade(
        timestamp=bittrex_trade['TimeStamp'],
        pair=pair,
        type=order_type,
        rate=rate,
        cost=cost,
        cost_currency=base_currency,
        fee=fee,
        fee_currency=base_currency,
        amount=amount,
        location='bittrex'
    )


class Bittrex(Exchange):
    def __init__(self, api_key, secret, kraken):
        super(Bittrex, self).__init__('bittrex', api_key, secret)
        self.apiversion = 'v1.1'
        self.uri = 'https://bittrex.com/api/{}/'.format(self.apiversion)
        # TODO: Remove this dependency. This is just to query the BTC/USD value
        #       easily and without further calls to other APIs. But this should go
        #       away since a user may not have a kraken account
        self.kraken = kraken

    def api_query(self, method, options=None):
        """
        Queries Bittrex with given method and options
        """
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))
        method_type = 'public'

        if method in BITTREX_MARKET_METHODS:
            method_type = 'market'
        elif method in BITTREX_ACCOUNT_METHODS:
            method_type = 'account'

        request_url = self.uri + method_type + '/' + method + '?'

        if method_type != 'public':
            request_url += 'apikey=' + self.api_key + "&nonce=" + nonce + '&'

        request_url += urllib.urlencode(options)
        # signature = hmac.new(
        #     base64.b64decode(self.secret),
        #     request_url.encode(),
        #     hashlib.sha512
        # )
        signature = hmac.new(self.secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()
        headers = {'apisign': signature}
        ret = urllib2.urlopen(
            urllib2.Request(request_url, headers=headers)
        )
        json_ret = json.loads(ret.read())
        if json_ret['success'] is not True:
            raise ValueError(json_ret['message'])
        return json_ret['result']

    def find_usd_price(self, asset):
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']

        btc_pair = 'BTC-' + asset
        for market in self.markets:
            if market['MarketName'] == btc_pair:
                btc_price = market['Last']
                return btc_price * self.kraken.usdprice['BTC']

        # if we get here we did not find a price
        raise ValueError('Could not find a BTC market for "{}"'.format(asset))

    def query_balances(self):
        self.markets = self.api_query('getmarketsummaries')

        resp = self.api_query('getbalances')
        returned_balances = dict()
        for entry in resp:
            currency = entry['Currency']
            balance = dict()
            balance['amount'] = entry['Balance']
            balance['usd_value'] = balance['amount'] * self.find_usd_price(currency)
            returned_balances[currency] = balance

        return returned_balances

    def query_trade_history(
            self,
            start_ts=None,
            end_ts=ts_now(),
            market=None,
            count=None):

        options = dict()
        if market is not None:
            options['market'] = world_pair_to_bittrex(market)
        if count is not None:
            options['count'] = count
        order_history = self.api_query('getorderhistory', options)

        returned_history = list()
        for order in order_history:
            order_timestamp = createTimeStamp(order['TimeStamp'], formatstr="%Y-%m-%dT%H:%M:%S.%f")
            if start_ts is not None and order_timestamp < start_ts:
                continue
            if end_ts is not None and order_timestamp > end_ts:
                break
            order['TimeStamp'] = order_timestamp
            returned_history.append(trade_from_bittrex(order))

        return returned_history
