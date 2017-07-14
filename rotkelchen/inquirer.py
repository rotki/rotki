import urllib2
from fval import FVal
from utils import rlk_jsonloads


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
        else:
            resp = urllib2.urlopen(
                urllib2.Request(
                    'https://min-api.cryptocompare.com/data/price?fsym={}&tsyms=USD'.format(
                        asset
                    ))
            )
            resp = rlk_jsonloads(resp.read())
            return FVal(resp['USD'])
