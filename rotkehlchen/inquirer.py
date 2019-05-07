from __future__ import unicode_literals

import logging
import os
from json.decoder import JSONDecodeError
from typing import Dict, Iterable, Optional

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import CURRENCYCONVERTER_API_KEY, ZERO
from rotkehlchen.constants.assets import FIAT_CURRENCIES, S_USD
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FiatAsset, FilePath, Price, Timestamp
from rotkehlchen.utils.misc import request_get_dict, retry_calls, ts_now, tsToDate
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_cryptocompare_for_fiat_price(asset: Asset) -> Price:
    log.debug('Get usd price from cryptocompare', asset=asset)
    cc_asset_str = asset.to_cryptocompare()
    resp = retry_calls(
        5,
        'find_usd_price',
        'requests.get',
        requests.get,
        u'https://min-api.cryptocompare.com/data/price?'
        'fsym={}&tsyms=USD'.format(cc_asset_str),
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
        return Price(ZERO)

    price = Price(FVal(resp['USD']))
    log.debug('Got usd price from cryptocompare', asset=asset, price=price)
    return price


def _query_exchanges_rateapi(base: FiatAsset, quote: FiatAsset) -> Optional[Price]:
    log.debug(
        'Querying api.exchangeratesapi.io fiat pair',
        base_currency=base,
        quote_currency=quote,
    )
    querystr = f'https://api.exchangeratesapi.io/latest?base={base}&symbols={quote}'
    try:
        resp = request_get_dict(querystr)
        return Price(FVal(resp['rates'][quote]))
    except (ValueError, RemoteError, KeyError, requests.exceptions.TooManyRedirects):
        log.error(
            'Querying api.exchangeratesapi.io for fiat pair failed',
            base_currency=base,
            quote_currency=quote,
        )
        return None


def _query_currency_converterapi(base: FiatAsset, quote: FiatAsset) -> Optional[Price]:
    log.debug(
        'Query free.currencyconverterapi.com fiat pair',
        base_currency=base,
        quote_currency=quote,
    )
    pair = f'{base}_{quote}'
    querystr = (
        f'https://free.currencyconverterapi.com/api/v6/convert?'
        f'q={pair}&apiKey={CURRENCYCONVERTER_API_KEY}'
    )
    try:
        resp = request_get_dict(querystr)
        return Price(FVal(resp['results'][pair]['val']))
    except (ValueError, RemoteError, KeyError):
        log.error(
            'Querying free.currencyconverterapi.com fiat pair failed',
            base_currency=base,
            quote_currency=quote,
        )
        return None


class Inquirer(object):
    __instance = None
    _cached_forex_data: Dict
    _data_directory: FilePath

    def __new__(cls, data_dir: FilePath = None):
        if Inquirer.__instance is not None:
            return Inquirer.__instance

        assert data_dir, 'arguments should be given at the first instantiation'

        Inquirer.__instance = object.__new__(cls)

        Inquirer.__instance._data_directory = data_dir
        filename = os.path.join(data_dir, 'price_history_forex.json')
        try:
            with open(filename, 'r') as f:
                # we know price_history_forex contains a dict
                data = rlk_jsonloads_dict(f.read())
                Inquirer.__instance._cached_forex_data = data
        except (OSError, IOError, JSONDecodeError):
            Inquirer.__instance._cached_forex_data = dict()

        return Inquirer.__instance

    @staticmethod
    def find_usd_price(
            asset: Asset,
            asset_btc_price: Optional[FVal] = None,
    ) -> Price:
        return query_cryptocompare_for_fiat_price(asset)

    @staticmethod
    def get_fiat_usd_exchange_rates(
            currencies: Optional[Iterable[FiatAsset]] = None,
    ) -> Dict[FiatAsset, FVal]:
        rates = {S_USD: FVal(1)}
        if not currencies:
            currencies = FIAT_CURRENCIES[1:]
        for currency in currencies:
            rates[currency] = Inquirer().query_fiat_pair(S_USD, currency)
        return rates

    @staticmethod
    def query_historical_fiat_exchange_rates(
            from_fiat_currency: FiatAsset,
            to_fiat_currency: FiatAsset,
            timestamp: Timestamp,
    ) -> Optional[Price]:
        date = tsToDate(timestamp, formatstr='%Y-%m-%d')
        instance = Inquirer()
        rate = instance._get_cached_forex_data(date, from_fiat_currency, to_fiat_currency)
        if rate:
            return rate

        log.debug(
            'Querying exchangeratesapi',
            from_fiat_currency=from_fiat_currency,
            to_fiat_currency=to_fiat_currency,
            timestamp=timestamp,
        )

        query_str = (
            f'https://api.exchangeratesapi.io/{date}?'
            f'base={from_fiat_currency}'
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

        if 'rates' not in result or to_fiat_currency not in result['rates']:
            return None

        if date not in instance._cached_forex_data:
            instance._cached_forex_data[date] = {}

        if from_fiat_currency not in instance._cached_forex_data[date]:
            instance._cached_forex_data[date][from_fiat_currency] = {}

        for key, value in result['rates'].items():
            instance._cached_forex_data[date][from_fiat_currency][key] = FVal(value)

        rate = Price(FVal(result['rates'][to_fiat_currency]))
        log.debug('Exchangeratesapi query succesful', rate=rate)
        return rate

    @staticmethod
    def _save_forex_rate(
            date: str,
            from_currency: FiatAsset,
            to_currency: FiatAsset,
            price: FVal,
    ):
        instance = Inquirer()
        if date not in instance._cached_forex_data:
            instance._cached_forex_data[date] = {}

        if from_currency not in instance._cached_forex_data[date]:
            instance._cached_forex_data[date][from_currency] = {}

        msg = 'Cached value should not already exist'
        assert to_currency not in instance._cached_forex_data[date][from_currency], msg
        instance._cached_forex_data[date][from_currency][to_currency] = price
        instance.save_historical_forex_data()

    @staticmethod
    def _get_cached_forex_data(
            date: str,
            from_currency: FiatAsset,
            to_currency: FiatAsset,
    ) -> Optional[Price]:
        instance = Inquirer()
        if date in instance._cached_forex_data:
            if from_currency in instance._cached_forex_data[date]:
                rate = instance._cached_forex_data[date][from_currency].get(to_currency)
                if rate:
                    log.debug(
                        'Got cached forex rate',
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                    )
                return rate
        return None

    @staticmethod
    def save_historical_forex_data() -> None:
        instance = Inquirer()
        filename = os.path.join(instance._data_directory, 'price_history_forex.json')
        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(instance._cached_forex_data))

    @staticmethod
    def query_fiat_pair(base: FiatAsset, quote: FiatAsset) -> Price:
        if base == quote:
            return Price(FVal('1'))

        instance = Inquirer()
        now = ts_now()
        date = tsToDate(ts_now(), formatstr='%Y-%m-%d')
        price = instance._get_cached_forex_data(date, base, quote)
        if price:
            return price

        price = _query_exchanges_rateapi(base, quote)
        if not price:
            price = _query_currency_converterapi(base, quote)

        if not price:
            # Search the cache for any price in the last month
            for i in range(1, 31):
                now = Timestamp(now - Timestamp(86401))
                date = tsToDate(now, formatstr='%Y-%m-%d')
                price = instance._get_cached_forex_data(date, base, quote)
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

        instance._save_forex_rate(date, base, quote, price)
        return price
