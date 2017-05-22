import json
import urllib2


class Inquirer(object):
    def __init__(self, kraken=None):
        self.kraken = kraken

    def query_kraken_for_price(self, asset, asset_btc_price):
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']
        return asset_btc_price * self.kraken.usdprice['BTC']

    def find_usd_price(self, asset, asset_btc_price=None):
        if self.kraken and self.kraken.first_connection_made:
            return self.query_kraken_for_price(asset, asset_btc_price)
        else:
            coinmarketcap_resp = urllib2.urlopen(
                urllib2.Request('https://api.coinmarketcap.com/v1/ticker/')
            )
            coinmarketcap_resp = json.loads(coinmarketcap_resp.read())
            for result in coinmarketcap_resp:
                if result['symbol'] == asset:
                    return float(result['price_usd'])

            raise ValueError('Could not find a USD price for "{}"'.format(asset))
