from __future__ import unicode_literals
from urllib.request import Request, urlopen

from rotkehlchen.fval import FVal
from rotkehlchen.utils import rlk_jsonloads, retry_calls, query_fiat_pair

import logging
logger = logging.getLogger(__name__)

FIAT_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CNY']


def get_fiat_usd_exchange_rates(currencies=None):
    rates = {'USD': 1}
    if not currencies:
        currencies = FIAT_CURRENCIES[1:]
    for currency in currencies:
        rates[currency] = query_fiat_pair('USD', currency)

    return rates


class Inquirer(object):
    def __init__(self, kraken=None):
        self.kraken = kraken

    def query_kraken_for_price(self, asset, asset_btc_price):
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']
        return asset_btc_price * self.kraken.usdprice['BTC']

    def find_usd_price(self, asset, asset_btc_price=None):
        if self.kraken and self.kraken.first_connection_made and asset_btc_price is not None:
            return self.query_kraken_for_price(asset, asset_btc_price)

        # Adjust some ETH tokens to how cryptocompare knows them
        if asset == 'RDN':
            asset = 'RDN*'  # temporary
        if asset == 'DATAcoin':
            asset = 'DATA'
        resp = retry_calls(
            5,
            'find_usd_price',
            'urllib2.urlopen',
            urlopen,
            Request(
                u'https://min-api.cryptocompare.com/data/price?fsym={}&tsyms=USD'.format(
                    asset
                ))
        )

        resp = rlk_jsonloads(resp.read())

        # If there is an error in the response skip this token
        if 'USD' not in resp:
            if resp['Response'] == 'Error':
                print('Could not query USD price for {}. Error: "{}"'.format(
                    asset,
                    resp['Message']),
                )
            else:
                print('Could not query USD price for {}'.format(asset))
            return FVal(0)

        return FVal(resp['USD'])
