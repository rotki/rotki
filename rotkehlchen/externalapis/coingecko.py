import json
import logging
from typing import Any, Dict, List, NamedTuple, Optional, Union, overload
from urllib.parse import urlencode

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS, DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import RemoteError, UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.misc import create_timestamp, timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

COINGECKO_QUERY_RETRY_TIMES = 4


class CoingeckoAssetData(NamedTuple):
    identifier: str
    symbol: str
    name: str
    description: str
    image_url: str


DELISTED_ASSETS = [
    strethaddress_to_identifier('0x0F72714B35a366285Df85886A2eE174601292A17'),
    'FLUZ',
    'EBCH',
    'GOLOS',
    'NPER',
    strethaddress_to_identifier('0xCA29db4221c111888a7e80b12eAc8a266Da3Ee0d'),
    'ADN',
    'PIX',
    strethaddress_to_identifier('0xdfdc0D82d96F8fd40ca0CFB4A288955bECEc2088'),
    'LKY',
    strethaddress_to_identifier('0xaFBeC4D65BC7b116d85107FD05d912491029Bf46'),
    strethaddress_to_identifier('0x37D40510a2F5Bc98AA7a0f7BF4b3453Bcfb90Ac1'),
    'BITCAR',
    strethaddress_to_identifier('0x499A6B77bc25C26bCf8265E2102B1B3dd1617024'),
    'OLE',
    'ROC',
    'VIN',
    'FIH',
    strethaddress_to_identifier('0x899338b84D25aC505a332aDCE7402d697D947494'),
    'ADH',
    'AUR',
    strethaddress_to_identifier('0x2A05d22DB079BC40C2f77a1d1fF703a56E631cc1'),
    'BYC',
    'DGS',
    strethaddress_to_identifier('0xb3Bd49E28f8F832b8d1E246106991e546c323502'),
    'HST',
    'INS',
    'IPSX',
    'SHP',
    'WDC',
    'BOST',
    'FND',
    'LDC',
    'ORI',
    'RIPT',
    'SGR',
    'LOCUS',
    'REDC',
    'SGN',
    strethaddress_to_identifier('0xD65960FAcb8E4a2dFcb2C2212cb2e44a02e2a57E'),
    strethaddress_to_identifier('0xD9A12Cde03a86E800496469858De8581D3A5353d'),
    'AC',
    strethaddress_to_identifier('0x4C0fBE1BB46612915E7967d2C3213cd4d87257AD'),
    'BITPARK',
    strethaddress_to_identifier('0xB4b1D2C217EC0776584CE08D3DD98F90EDedA44b'),
    'DAN',
    strethaddress_to_identifier('0x89c6c856a6db3e46107163D0cDa7A7FF211BD655'),
    strethaddress_to_identifier('0x07e3c70653548B04f0A75970C1F81B4CBbFB606f'),
    'DROP',
    'ERD',
    'ETBS',
    strethaddress_to_identifier('0x543Ff227F64Aa17eA132Bf9886cAb5DB55DCAddf'),
    'STP',
    'SYNC',
    'TBT',
    'TNT',
    'WIC',
    'XCN',
    strethaddress_to_identifier('0x6368e1E18c4C419DDFC608A0BEd1ccb87b9250fc'),
    'FREC',
    'PTC',
    strethaddress_to_identifier('0x13F1b7FDFbE1fc66676D56483e21B1ecb40b58E2'),
    'J8T',
    'MRK',
    'TTV',
    'ALX',
    'EBC',
    'RCN-2',
    'SKYM',
    strethaddress_to_identifier('0xFA456Cf55250A839088b27EE32A424d7DAcB54Ff'),
    strethaddress_to_identifier('0x12fCd6463E66974cF7bBC24FFC4d40d6bE458283'),
    strethaddress_to_identifier('0x3A1237D38D0Fb94513f85D61679cAd7F38507242'),
    strethaddress_to_identifier('0xf333b2Ace992ac2bBD8798bF57Bc65a06184afBa'),
    strethaddress_to_identifier('0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7'),
    'aLEND',
    'aREP',
    'CRBT',
    'EXC-2',
    strethaddress_to_identifier('0x1da015eA4AD2d3e5586E54b9fB0682Ca3CA8A17a'),
    'CZR',
    'ROCK2',
    'ATMI',
    strethaddress_to_identifier('0x9B11EFcAAA1890f6eE52C6bB7CF8153aC5d74139'),
    strethaddress_to_identifier('0xc88Be04c809856B75E3DfE19eB4dCf0a3B15317a'),
    'CREDO',
    'ETK',
    'FNKOS',
    strethaddress_to_identifier('0x2AEC18c5500f21359CE1BEA5Dc1777344dF4C0Dc'),
    'GIM',
    strethaddress_to_identifier('0xA4eA687A2A7F29cF2dc66B39c68e4411C0D00C49'),
    'KORE',
    'NBAI',
    strethaddress_to_identifier('0xfeDAE5642668f8636A11987Ff386bfd215F942EE'),
    'XEL',
    'ATS',
    'BCY',
    'yDAI+yUSDC+yUSDT+yBUSD',
    'yyDAI+yUSDC+yUSDT+yBUSD',
    'ypaxCrv',
    'crvRenWBTC',
    'crvRenWSBTC',
    'ycrvRenWSBTC',
    'SPRK',
    'VV',
    'DRP',
    'HBZ',
    'TAAS',
    'TRUMPLOSE',
    'TRUMPWIN',
    'ATX-2',
    'SONIQ',
    'TRUST',
    'CDX',
    'CRB',
    'CTX',
    'EGC',
    'ICOS',
    'MTRC',
    'NOX',
    'PHI',
    'RLT',
    'SPIN',
    'VIEW',
    'VRM',
    strethaddress_to_identifier('0xdF1D6405df92d981a2fB3ce68F6A03baC6C0E41F'),
    'SPF',
    'NOBS',
    'DADI',
    strethaddress_to_identifier('0x22dE9912cd3D74953B1cd1F250B825133cC2C1b3'),
    strethaddress_to_identifier('0xAa0bb10CEc1fa372eb3Abc17C933FC6ba863DD9E'),
    strethaddress_to_identifier('0x1BcBc54166F6bA149934870b60506199b6C9dB6D'),
    strethaddress_to_identifier('0x851017523AE205adc9195e7F97D029f4Cfe7794c'),
    strethaddress_to_identifier('0x7f65BE7FAd0c22813e51746E7e8f13a20bAa9411'),
    strethaddress_to_identifier('0xe431a4c5DB8B73c773e06cf2587dA1EB53c41373'),
    strethaddress_to_identifier('0xAef38fBFBF932D1AeF3B808Bc8fBd8Cd8E1f8BC5'),
    strethaddress_to_identifier('0xd341d1680Eeee3255b8C4c75bCCE7EB57f144dAe'),
    'FLO',
    strethaddress_to_identifier('0x06147110022B768BA8F99A8f385df11a151A9cc8'),
    strethaddress_to_identifier('0x27695E09149AdC738A978e9A678F99E4c39e9eb9'),
]

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

    def __init__(self) -> None:
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.all_coins_cache: Optional[Dict[str, Dict[str, Any]]] = None

    @overload
    def _query(
            self,
            module: Literal['coins/list'],
            subpath: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        ...

    @overload
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
                response = self.session.get(
                    f'{url}?{urlencode(options)}',
                    timeout=DEFAULT_TIMEOUT_TUPLE,
                )
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
            decoded_json = json.loads(response.text)
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
                image_url=data['image']['small'],
            )
        except KeyError as e:
            raise RemoteError(
                f'Missing expected key entry {e} in coingecko coin data response',
            ) from e

        return parsed_data

    def all_coins(self) -> Dict[str, Dict[str, Any]]:
        if self.all_coins_cache is None:
            response = self._query(module='coins/list')
            self.all_coins_cache = {}
            for entry in response:
                if entry['id'] in self.all_coins_cache:
                    log.warning(
                        f'Found duplicate coingecko identifier {entry["id"]} when querying '
                        f'the list of coingecko assets. Ignoring...',
                    )
                    continue

                identifier = entry.pop('id')
                self.all_coins_cache[identifier] = entry

        return self.all_coins_cache

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

    def query_current_price(self, from_asset: Asset, to_asset: Asset) -> Price:
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

        try:
            from_coingecko_id = from_asset.to_coingecko()
        except UnsupportedAsset:
            log.warning(
                f'Tried to query coingecko simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
            )
            return Price(ZERO)

        result = self._query(
            module='simple/price',
            options={
                'ids': from_coingecko_id,
                'vs_currencies': vs_currency,
            })

        try:
            return Price(FVal(result[from_coingecko_id][vs_currency]))
        except KeyError as e:
            log.warning(
                f'Queried coingecko simple price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But got key error for {str(e)} when '
                f'processing the result.',
            )
            return Price(ZERO)

    def can_query_history(  # pylint: disable=no-self-use
            self,
            from_asset: Asset,  # pylint: disable=unused-argument
            to_asset: Asset,  # pylint: disable=unused-argument
            timestamp: Timestamp,  # pylint: disable=unused-argument
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return True  # noop for coingecko

    def rate_limited_in_last(  # pylint: disable=no-self-use
            self,
            seconds: Optional[int] = None,  # pylint: disable=unused-argument
    ) -> bool:
        return False  # noop for coingecko

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        vs_currency = Coingecko.check_vs_currencies(
            from_asset=from_asset,
            to_asset=to_asset,
            location='historical price',
        )
        if not vs_currency:
            return Price(ZERO)

        try:
            from_coingecko_id = from_asset.to_coingecko()
        except UnsupportedAsset:
            log.warning(
                f'Tried to query coingecko historical price from {from_asset.identifier} '
                f'to {to_asset.identifier}. But from_asset is not supported in coingecko',
            )
            return Price(ZERO)

        # check DB cache
        price_cache_entry = GlobalDBHandler().get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=DAY_IN_SECONDS,
            source=HistoricalPriceOracle.COINGECKO,
        )
        if price_cache_entry:
            return price_cache_entry.price

        # no cache, query coingecko for daily price
        date = timestamp_to_date(timestamp, formatstr='%d-%m-%Y')
        result = self._query(
            module='coins',
            subpath=f'{from_coingecko_id}/history',
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

        # save result in the DB and return
        date_timestamp = create_timestamp(date, formatstr='%d-%m-%Y')
        GlobalDBHandler().add_historical_prices(entries=[HistoricalPrice(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.COINGECKO,
            timestamp=date_timestamp,
            price=price,
        )])
        return price
