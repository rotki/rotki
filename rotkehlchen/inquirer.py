from __future__ import unicode_literals
import requests
from typing import Optional, Dict, Iterable, cast

from rotkehlchen.fval import FVal
from rotkehlchen.utils import rlk_jsonloads, retry_calls, query_fiat_pair
from rotkehlchen import typing
from rotkehlchen.constants import FIAT_CURRENCIES, S_USD, S_RDN, S_DATACOIN
from rotkehlchen.errors import RemoteError

import logging
logger = logging.getLogger(__name__)


def get_fiat_usd_exchange_rates(
        currencies: Optional[Iterable[typing.FiatAsset]] = None,
) -> Dict[typing.FiatAsset, FVal]:
    rates = {S_USD: FVal(1)}
    if not currencies:
        currencies = FIAT_CURRENCIES[1:]
    for currency in currencies:
        rates[currency] = query_fiat_pair(S_USD, currency)

    return rates


class Inquirer(object):
    def __init__(self, kraken=None):  # TODO: Add type after fixing cyclic dependency
        self.kraken = kraken
        self.session = requests.session()

    def query_kraken_for_price(
            self,
            asset: typing.Asset,
            asset_btc_price: FVal,
    ) -> FVal:
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']
        return asset_btc_price * self.kraken.usdprice['BTC']

    def find_usd_price(
            self,
            asset: typing.Asset,
            asset_btc_price: Optional[FVal] = None,
    ) -> FVal:
        if self.kraken and self.kraken.first_connection_made and asset_btc_price is not None:
            return self.query_kraken_for_price(asset, asset_btc_price)

        # Adjust some ETH tokens to how cryptocompare knows them
        if asset == S_RDN:
            asset = cast(typing.EthToken, 'RDN*')  # remove this if cryptocompare changes the symbol
        if asset == S_DATACOIN:
            asset = cast(typing.NonEthTokenBlockchainAsset, 'DATA')
        resp = retry_calls(
            5,
            'find_usd_price',
            'requests.get',
            requests.get,
            u'https://min-api.cryptocompare.com/data/price?'
            'fsym={}&tsyms=USD'.format(asset)
        )

        if resp.status_code != 200:
            raise RemoteError('Cant reach cryptocompare to get USD value of {}'.format(asset))

        resp = rlk_jsonloads(resp.text)

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
