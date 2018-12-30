from __future__ import unicode_literals

import logging
import os
from json.decoder import JSONDecodeError
from typing import Dict, Iterable, Optional, cast

import requests

from rotkehlchen import typing
from rotkehlchen.constants import FIAT_CURRENCIES, S_DATACOIN, S_IOTA, S_RDN, S_USD
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils import (
    query_fiat_pair,
    retry_calls,
    rlk_jsondumps,
    rlk_jsonloads,
    rlk_jsonloads_dict,
    tsToDate,
)

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


def query_cryptocompare_for_fiat_price(asset: typing.Asset) -> FVal:
    log.debug('Get usd price from cryptocompare', asset=asset)
    asset = world_to_cryptocompare(asset)
    resp = retry_calls(
        5,
        'find_usd_price',
        'requests.get',
        requests.get,
        u'https://min-api.cryptocompare.com/data/price?'
        'fsym={}&tsyms=USD'.format(asset),
    )

    if resp.status_code != 200:
        raise RemoteError('Cant reach cryptocompare to get USD value of {}'.format(asset))

    resp = rlk_jsonloads_dict(resp.text)

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


class Inquirer(object):
    def __init__(self, data_dir, kraken=None):
        self.kraken = kraken
        self.session = requests.session()
        self.data_directory = data_dir

        filename = os.path.join(self.data_directory, 'price_history_forex.json')
        try:
            with open(filename, 'rb') as f:
                data = rlk_jsonloads(f.read())
                self.cached_forex_data = data
        except (OSError, IOError, JSONDecodeError):
            self.cached_forex_data = dict()

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

        return query_cryptocompare_for_fiat_price(asset)

    def query_historical_fiat_exchange_rates(
            self,
            from_currency: typing.FiatAsset,
            to_currency: typing.FiatAsset,
            timestamp: typing.Timestamp,
    ) -> Optional[FVal]:
        date = tsToDate(timestamp, formatstr='%Y-%m-%d')
        if date in self.cached_forex_data:
            if from_currency in self.cached_forex_data[date]:
                rate = self.cached_forex_data[date][from_currency].get(to_currency)
                if rate:
                    log.debug(
                        'Got cached forex rate',
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                    )
                return rate

        log.debug(
            'Querying exchangeratesapi',
            from_currency=from_currency,
            to_currency=to_currency,
            timestamp=timestamp,
        )

        query_str = (
            f'https://api.exchangeratesapi.io/{date}?'
            f'base={from_currency}'
        )
        resp = retry_calls(
            5,
            'query_exchangeratesapi',
            'requests.get',
            requests.get,
            query_str,
        )

        if resp.status_code != 200:
            return None

        try:
            result = rlk_jsonloads_dict(resp.text)
        except JSONDecodeError:
            return None

        if 'rates' not in result or to_currency not in result['rates']:
            return None

        if date not in self.cached_forex_data:
            self.cached_forex_data[date] = {}

        if from_currency not in self.cached_forex_data[date]:
            self.cached_forex_data[date][from_currency] = {}

        for key, value in result['rates'].items():
            self.cached_forex_data[date][from_currency][key] = FVal(value)

        rate = FVal(result['rates'][to_currency])
        log.debug('Exchangeratesapi query succesful', rate=rate)
        return rate

    def save_historical_forex_data(self):
        filename = os.path.join(self.data_directory, 'price_history_forex.json')
        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(self.cached_forex_data))
