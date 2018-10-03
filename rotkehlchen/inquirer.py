from __future__ import unicode_literals

import logging
from typing import Dict, Iterable, Optional, cast

import requests

from rotkehlchen import typing
from rotkehlchen.constants import FIAT_CURRENCIES, S_DATACOIN, S_IOTA, S_RDN, S_USD
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils import query_fiat_pair, retry_calls, rlk_jsonloads

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def get_fiat_usd_exchange_rates(
        currencies: Optional[Iterable[typing.FiatAsset]] = None,
) -> Dict[typing.FiatAsset, FVal]:
    rates = {S_USD: FVal(1)}
    if not currencies:
        currencies = FIAT_CURRENCIES[1:]
    for currency in currencies:
        rates[currency] = query_fiat_pair(S_USD, currency)

    return rates


def world_to_cryptocompare(asset):
    # Adjust some ETH tokens to how cryptocompare knows them
    if asset == S_RDN:
        # remove this if cryptocompare changes the symbol
        asset = cast(typing.EthToken, 'RDN*')
    elif asset == S_DATACOIN:
        asset = cast(typing.NonEthTokenBlockchainAsset, 'DATA')
    elif asset == S_IOTA:
        asset = cast(typing.NonEthTokenBlockchainAsset, 'IOT')

    return asset


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
            price = self.query_kraken_for_price(asset, asset_btc_price)
            log.debug('Get usd price from kraken', asset=asset, price=price)
            return price

        log.debug('Get usd price from cryptocompare', asset=asset)
        asset = world_to_cryptocompare(asset)
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
            error_message = ''
            if resp['Response'] == 'Error':
                error_message = resp['Message']

            log.error(
                'Cryptocompare usd price query failed',
                asset=asset,
                error=error_message,
            )
            return FVal(0)

        price = FVal(resp['USD'])
        log.debug('Got usd price from cryptocompare', asset=asset, price=price)
        return price
