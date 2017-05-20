import json
import urllib2


class Inquirer(object):
    def __init__(self, kraken=None):
        self.kraken = kraken

    def query_kraken_for_price(self, asset):
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']

        btc_pair = 'BTC-' + asset
        for market in self.markets:
            if market['MarketName'] == btc_pair:
                btc_price = market['Last']
                return btc_price * self.kraken.usdprice['BTC']

        # if we get here we did not find a price
        raise ValueError('Could not find a BTC market for "{}"'.format(asset))

    def find_usd_price(self, asset):
        if self.kraken:
            return self.query_kraken_for_price(asset)
        else:
            coinmarketcap_resp = urllib2.urlopen(
                urllib2.Request('https://api.coinmarketcap.com/v1/ticker/')
            )
            coinmarketcap_resp = json.loads(coinmarketcap_resp.read())
            for result in coinmarketcap_resp:
                if result['symbol'] == asset:
                    return float(result['price_usd'])

            raise ValueError('Could not find a USD price for "{}"'.format(asset))
