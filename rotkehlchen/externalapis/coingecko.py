import json
import logging
import gevent
from typing import Any, Dict, List, NamedTuple, Optional, Union, overload
from urllib.parse import urlencode

import requests
from typing_extensions import Literal
from json.decoder import JSONDecodeError
from pathlib import Path

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsondumps, rlk_jsonloads
from rotkehlchen.utils.misc import timestamp_to_date
from rotkehlchen.utils.misc import get_or_make_price_history_dir

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PRICE_HISTORY_FILE_PREFIX = 'gecko_price_history_'
COINGECKO_QUERY_RETRY_TIMES = 4


class CoingeckoImageURLs(NamedTuple):
    thumb: str
    small: str
    large: str


class CoingeckoAssetData(NamedTuple):
    identifier: str
    symbol: str
    name: str
    description: str
    images: CoingeckoImageURLs


COINGECKO_SIMPLE_VS_CURRENCIES = [
    "btc",
    "eth",
    "ltc",
    "bch",
    "bnb",
    "eos",
    "xrp",
    "xlm",
    "link",
    "dot",
    "yfi",
    "usd",
    "aed",
    "ars",
    "aud",
    "bdt",
    "bhd",
    "bmd",
    "brl",
    "cad",
    "chf",
    "clp",
    "cny",
    "czk",
    "dkk",
    "eur",
    "gbp",
    "hkd",
    "huf",
    "idr",
    "ils",
    "inr",
    "jpy",
    "krw",
    "kwd",
    "lkr",
    "mmk",
    "mxn",
    "myr",
    "nok",
    "nzd",
    "php",
    "pkr",
    "pln",
    "rub",
    "sar",
    "sek",
    "sgd",
    "thb",
    "try",
    "twd",
    "uah",
    "vef",
    "vnd",
    "zar",
    "xdr",
    "xag",
    "xau",
]


class Coingecko():

    def __init__(self, data_directory: Path) -> None:
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.data_directory = data_directory

    @overload  # noqa: F811
    def _query(
            self,
            module: Literal['coins/list'],
            subpath: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @overload  # noqa: F811
    def _query(
            self,
            module: Literal['coins', 'simple/price'],
            subpath: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    def _query(
            self,
            module: str,
            subpath: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Performs a coingecko query

        May raise:
        - RemoteError if there is a problem querying coingecko
        """
        if options is None:
            options = {}
        url = f'https://api.coingecko.com/api/v3/{module}/'
        if subpath:
            url += subpath

        logger.debug(f'Querying coingecko: {url}?{urlencode(options)}')
        tries = COINGECKO_QUERY_RETRY_TIMES
        while tries >= 0:
            try:
                response = self.session.get(f'{url}?{urlencode(options)}')
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Coingecko API request failed due to {str(e)}') from e

            if response.status_code == 429:
                # Coingecko allows only 100 calls per minute. If you get 429 it means you
                # exceeded this and are throttled until the next minute window
                # backoff and retry 4 times =  2.5 + 3.33 + 5 + 10 = at most 20.8 secs
                if tries >= 1:
                    backoff_seconds = 10 / tries
                    log.debug(
                        f'Got rate limited by coingecko. '
                        f'Backing off for {backoff_seconds}',
                    )
                    gevent.sleep(backoff_seconds)
                    tries -= 1
                    continue

                # else
                log.debug(
                    f'Got rate limited by coingecko and did not manage to get a '
                    f'request through even after {COINGECKO_QUERY_RETRY_TIMES} '
                    f'incremental backoff retries',
                )

            break

        if response.status_code != 200:
            msg = (
                f'Coingecko API request {response.url} failed with HTTP status '
                f'code: {response.status_code}'
            )
            raise RemoteError(msg)

        try:
            decoded_json = rlk_jsonloads(response.text)
        except json.decoder.JSONDecodeError as e:
            msg = f'Invalid JSON in Coingecko response. {e}'
            raise RemoteError(msg) from e

        return decoded_json

    def asset_data(self, asset: Asset) -> CoingeckoAssetData:
        """

        May raise:
        - UnsupportedAsset() if the asset is not supported by coingecko
        - RemoteError if there is a problem querying coingecko
        """
        options = {
            # Include all localized languages in response (true/false) [default: true]
            'localization': False,
            # Include tickers data (true/false) [default: true]
            'tickers': False,
            # Include market_data (true/false) [default: true]
            'market_data': False,
            # Include communitydata (true/false) [default: true]
            'community_data': False,
            # Include developer data (true/false) [default: true]
            'developer_data': False,
            # Include sparkline 7 days data (eg. true, false) [default: false]
            'sparkline': False,
        }
        gecko_id = asset.to_coingecko()
        data = self._query(
            module='coins',
            subpath=f'{gecko_id}',
            options=options,
        )

        try:
            parsed_data = CoingeckoAssetData(
                identifier=gecko_id,
                symbol=data['symbol'],
                name=data['name'],
                description=data['description']['en'],
                images=CoingeckoImageURLs(
                    thumb=data['image']['thumb'],
                    small=data['image']['small'],
                    large=data['image']['large'],
                ),
            )
        except KeyError as e:
            raise RemoteError(
                f'Missing expected key entry {e} in coingecko coin data response',
            ) from e

        return parsed_data

    def all_coins(self) -> List[Dict[str, Any]]:
        return self._query(module='coins/list')

    @staticmethod
    def check_vs_currencies(from_asset: Asset, to_asset: Asset, location: str) -> Optional[str]:
        vs_currency = to_asset.identifier.lower()
        if vs_currency not in COINGECKO_SIMPLE_VS_CURRENCIES:
            log.warning(
                f'Tried to query coingecko {location} from {from_asset.identifier} '
                f'to {to_asset.identifier}. But to_asset is not supported',
            )
            return None

        return vs_currency

    def simple_price(self, from_asset: Asset, to_asset: Asset) -> Price:
        """Returns a simple price for from_asset to to_asset in coingecko

        Uses the simple/price endpoint of coingecko. If to_asset is not part of the
        coingecko simple vs currencies or if from_asset is not supported in coingecko
        price zero is returned.

        May raise:
        - RemoteError if there is a problem querying coingecko
        """
        vs_currency = Coingecko.check_vs_currencies(
            from_asset=from_asset,
            to_asset=to_asset,
            location='simple price',
        )
        if not vs_currency:
            return Price(ZERO)

        if from_asset.coingecko is None:
            log.warning(
                f'Tried to query coingecko simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
            )
            return Price(ZERO)

        result = self._query(
            module='simple/price',
            options={
                'ids': from_asset.coingecko,
                'vs_currencies': vs_currency,
            })

        try:
            return Price(FVal(result[from_asset.coingecko][vs_currency]))
        except KeyError as e:
            log.warning(
                f'Queried coingecko simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {str(e)} when '
                f'processing the result.',
            )
            return Price(ZERO)

    def _get_cached_price(self, from_asset: Asset, to_asset: Asset, date: str) -> Optional[Price]:
        price_history_dir = get_or_make_price_history_dir(self.data_directory)
        filename = (
            price_history_dir /
            f'{PRICE_HISTORY_FILE_PREFIX }{from_asset.identifier}_{to_asset.identifier}.json'
        )
        if not filename.is_file():
            return None

        with open(filename, 'r') as f:
            try:
                data: Dict[str, Price] = rlk_jsonloads_dict(f.read())
            except JSONDecodeError:
                return None

        if not isinstance(data, dict):
            return None

        return data.get(date, None)

    def _save_cached_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            date: str,
            price: Price,
    ) -> None:
        price_history_dir = get_or_make_price_history_dir(self.data_directory)
        filename = (
            price_history_dir /
            f'{PRICE_HISTORY_FILE_PREFIX }{from_asset.identifier}_{to_asset.identifier}.json'
        )
        data: Dict[str, Price] = {}
        if filename.is_file():
            with open(filename, 'r') as f:
                try:
                    data = rlk_jsonloads_dict(f.read())
                except JSONDecodeError:
                    data = {}

        if not isinstance(data, dict):
            data = {}

        data[date] = price
        with open(filename, 'w') as outfile:
            outfile.write(rlk_jsondumps(data))

    def historical_price(self, from_asset: Asset, to_asset: Asset, time: Timestamp) -> Price:
        vs_currency = Coingecko.check_vs_currencies(
            from_asset=from_asset,
            to_asset=to_asset,
            location='historical price',
        )
        if not vs_currency:
            return Price(ZERO)

        if from_asset.coingecko is None:
            log.warning(
                f'Tried to query coingecko historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
            )
            return Price(ZERO)

        date = timestamp_to_date(time, formatstr='%d-%m-%Y')
        cached_price = self._get_cached_price(from_asset=from_asset, to_asset=to_asset, date=date)
        if cached_price is not None:
            return cached_price

        result = self._query(
            module='coins',
            subpath=f'{from_asset.coingecko}/history',
            options={
                'date': date,
                'localization': False,
            },
        )

        try:
            price = Price(FVal(result['market_data']['current_price'][vs_currency]))
        except KeyError as e:
            log.warning(
                f'Queried coingecko historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {str(e)} when '
                f'processing the result.',
            )
            return Price(ZERO)

        self._save_cached_price(from_asset, to_asset, date, price)
        return price
