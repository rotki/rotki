from __future__ import unicode_literals

import logging
import os
from json.decoder import JSONDecodeError
from typing import Dict, Iterable, Optional, cast

import requests

from rotkehlchen.constants import (
    FIAT_CURRENCIES,
    S_BQX,
    S_DATACOIN,
    S_IOTA,
    S_NANO,
    S_RAIBLOCKS,
    S_RDN,
    S_USD,
    XRB_NANO_REBRAND_TS,
)
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    Asset,
    EthToken,
    FiatAsset,
    FilePath,
    NonEthTokenBlockchainAsset,
    Timestamp,
)
from rotkehlchen.utils import (
    request_get_dict,
    retry_calls,
    rlk_jsondumps,
    rlk_jsonloads_dict,
    ts_now,
    tsToDate,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def world_to_cryptocompare(asset: Asset, timestamp: Timestamp = None) -> Asset:
    # Adjust some ETH tokens to how cryptocompare knows them
    if asset == S_RDN:
        # remove this if cryptocompare changes the symbol
        asset = cast(EthToken, 'RDN*')
    elif asset == S_DATACOIN:
        asset = cast(NonEthTokenBlockchainAsset, 'DATA')
    elif asset == S_IOTA:
        asset = cast(NonEthTokenBlockchainAsset, 'IOT')
    elif asset == S_BQX:
        asset = cast(EthToken, 'ETHOS')
    elif asset == S_NANO and timestamp and timestamp < XRB_NANO_REBRAND_TS:
        return S_RAIBLOCKS
    elif asset == S_RAIBLOCKS and timestamp and timestamp >= XRB_NANO_REBRAND_TS:
        return S_NANO

    return asset


def query_cryptocompare_for_fiat_price(asset: Asset) -> FVal:
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


def _query_exchanges_rateapi(base: FiatAsset, quote: FiatAsset) -> Optional[FVal]:
    log.debug(
        'Querying api.exchangeratesapi.io fiat pair',
        base_currency=base,
        quote_currency=quote,
    )
    querystr = f'https://api.exchangeratesapi.io/latest?base={base}&symbols={quote}'
    try:
        resp = request_get_dict(querystr)
        return FVal(resp['rates'][quote])
    except (ValueError, RemoteError, KeyError):
        log.error(
            'Querying api.exchangeratesapi.io for fiat pair failed',
            base_currency=base,
            quote_currency=quote,
        )
        return None


def _query_currency_converterapi(base: FiatAsset, quote: FiatAsset) -> Optional[FVal]:
    log.debug(
        'Query free.currencyconverterapi.com fiat pair',
        base_currency=base,
        quote_currency=quote,
    )
    pair = '{}_{}'.format(base, quote)
    querystr = 'https://free.currencyconverterapi.com/api/v5/convert?q={}'.format(pair)
    try:
        resp = request_get_dict(querystr)
        return FVal(resp['results'][pair]['val'])
    except (ValueError, RemoteError, KeyError):
        log.error(
            'Querying free.currencyconverterapi.com fiat pair failed',
            base_currency=base,
            quote_currency=quote,
        )
        return None


class Inquirer(object):
    def __init__(self, data_dir: FilePath, kraken=None):
        self.kraken = kraken
        self.session = requests.session()
        self.data_directory = data_dir

        filename = os.path.join(self.data_directory, 'price_history_forex.json')
        try:
            with open(filename, 'r') as f:
                # we know price_history_forex contains a dict
                data = rlk_jsonloads_dict(f.read())
                self.cached_forex_data = data
        except (OSError, IOError, JSONDecodeError):
            self.cached_forex_data = dict()

    def query_kraken_for_price(
            self,
            asset: Asset,
            asset_btc_price: FVal,
    ) -> FVal:
        if asset == 'BTC':
            return self.kraken.usdprice['BTC']
        return asset_btc_price * self.kraken.usdprice['BTC']

    def find_usd_price(
            self,
            asset: Asset,
            asset_btc_price: Optional[FVal] = None,
    ) -> FVal:
        if self.kraken and self.kraken.first_connection_made and asset_btc_price is not None:
            price = self.query_kraken_for_price(asset, asset_btc_price)
            log.debug('Get usd price from kraken', asset=asset, price=price)
            return price

        return query_cryptocompare_for_fiat_price(asset)

    def get_fiat_usd_exchange_rates(
            self,
            currencies: Optional[Iterable[FiatAsset]] = None,
    ) -> Dict[FiatAsset, FVal]:
        rates = {S_USD: FVal(1)}
        if not currencies:
            currencies = FIAT_CURRENCIES[1:]
        for currency in currencies:
            rates[currency] = self.query_fiat_pair(S_USD, currency)
        return rates

    def query_historical_fiat_exchange_rates(
            self,
            from_currency: FiatAsset,
            to_currency: FiatAsset,
            timestamp: Timestamp,
    ) -> Optional[FVal]:
        date = tsToDate(timestamp, formatstr='%Y-%m-%d')
        rate = self._get_cached_forex_data(date, from_currency, to_currency)
        if rate:
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

    def _save_forex_rate(
            self,
            date: str,
            from_currency: FiatAsset,
            to_currency: FiatAsset,
            price: FVal,
    ):
        if date not in self.cached_forex_data:
            self.cached_forex_data[date] = {}

        if from_currency not in self.cached_forex_data[date]:
            self.cached_forex_data[date][from_currency] = {}

        msg = 'Cached value should not already exist'
        assert to_currency not in self.cached_forex_data[date][from_currency], msg
        self.cached_forex_data[date][from_currency][to_currency] = price
        self.save_historical_forex_data()

    def _get_cached_forex_data(
            self,
            date: str,
            from_currency: FiatAsset,
            to_currency: FiatAsset,
    ) -> Optional[FVal]:
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
        return None

    def save_historical_forex_data(self) -> None:
        filename = os.path.join(self.data_directory, 'price_history_forex.json')
        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(self.cached_forex_data))

    def query_fiat_pair(self, base: FiatAsset, quote: FiatAsset) -> FVal:
        if base == quote:
            return FVal(1.0)

        now = ts_now()
        date = tsToDate(ts_now(), formatstr='%Y-%m-%d')
        price = self._get_cached_forex_data(date, base, quote)
        if price:
            return price

        price = _query_currency_converterapi(base, quote)
        if not price:
            price = _query_exchanges_rateapi(base, quote)

        if not price:
            # Search the cache for any price in the last month
            for i in range(1, 31):
                now = Timestamp(now - Timestamp(86401))
                date = tsToDate(now, formatstr='%Y-%m-%d')
                price = self._get_cached_forex_data(date, base, quote)
                if price:
                    log.debug(
                        f'Could not query online apis for a fiat price. '
                        f'Used cached value from {i} days ago.',
                        base_currency=base,
                        quote_currency=quote,
                        price=price,
                    )
                    return price

            raise ValueError('Could not find a "{}" price for "{}"'.format(base, quote))

        self._save_forex_rate(date, base, quote, price)
        return price
