import logging
import os
import re
from collections import deque
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    NewType,
    Optional,
    Tuple,
)

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_COMP, A_DAI, A_USD, A_USDT, A_WETH
from rotkehlchen.errors import (
    NoPriceForGivenTimestamp,
    PriceQueryUnsupportedAsset,
    RemoteError,
    UnsupportedAsset,
)
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import (
    convert_to_int,
    get_or_make_price_history_dir,
    timestamp_to_date,
    ts_now,
)
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PRICE_HISTORY_FILE_PREFIX = 'cc_price_history_'


T_PairCacheKey = str
PairCacheKey = NewType('PairCacheKey', T_PairCacheKey)

RATE_LIMIT_MSG = 'You are over your rate limit please upgrade your account!'
CRYPTOCOMPARE_QUERY_RETRY_TIMES = 3
CRYPTOCOMPARE_RATE_LIMIT_WAIT_TIME = 60
CRYPTOCOMPARE_SPECIAL_CASES_MAPPING = {
    Asset('TLN'): A_WETH,
    Asset('BLY'): A_USDT,
    Asset('cDAI'): A_DAI,
    Asset('cCOMP'): A_COMP,
    Asset('cBAT'): Asset('BAT'),
    Asset('cREP'): Asset('REP'),
    Asset('cSAI'): Asset('SAI'),
    Asset('cUSDC'): Asset('USDC'),
    Asset('cUSDT'): A_USDT,
    Asset('cWBTC'): Asset('WBTC'),
    Asset('cUNI'): Asset('UNI'),
    Asset('cZRX'): Asset('ZRX'),
    Asset('ADADOWN'): A_USDT,
    Asset('ADAUP'): A_USDT,
    Asset('BNBDOWN'): A_USDT,
    Asset('BNBUP'): A_USDT,
    Asset('BTCDOWN'): A_USDT,
    Asset('BTCUP'): A_USDT,
    Asset('ETHDOWN'): A_USDT,
    Asset('ETHUP'): A_USDT,
    Asset('EOSDOWN'): A_USDT,
    Asset('EOSUP'): A_USDT,
    Asset('DOTDOWN'): A_USDT,
    Asset('DOTUP'): A_USDT,
    Asset('LTCDOWN'): A_USDT,
    Asset('LTCUP'): A_USDT,
    Asset('TRXDOWN'): A_USDT,
    Asset('TRXUP'): A_USDT,
    Asset('XRPDOWN'): A_USDT,
    Asset('XRPUP'): A_USDT,
    Asset('DEXT'): A_USDT,
    Asset('DOS'): A_USDT,
    Asset('GEEQ'): A_USDT,
    Asset('LINKDOWN'): A_USDT,
    Asset('LINKUP'): A_USDT,
    Asset('XTZDOWN'): A_USDT,
    Asset('XTZUP'): A_USDT,
    Asset('STAKE'): A_USDT,
    Asset('MCB'): A_USDT,
    Asset('TRB'): A_USDT,
    Asset('YFI'): A_USDT,
    Asset('YAM'): A_USDT,
    Asset('DEC-2'): A_USDT,
    Asset('ORN'): A_USDT,
    Asset('PERX'): A_USDT,
    Asset('PRQ'): A_USDT,
    Asset('RING'): A_USDT,
    Asset('SBREE'): A_USDT,
    Asset('YFII'): A_USDT,
    Asset('BZRX'): A_USDT,
    Asset('CREAM'): A_USDT,
    Asset('ADEL'): A_USDT,
    Asset('ANK'): A_USDT,
    Asset('CORN'): A_USDT,
    Asset('SAL'): A_USDT,
    Asset('CRT'): A_USDT,
    Asset('FSW'): A_USDT,
    Asset('JFI'): A_USDT,
    Asset('PEARL'): A_USDT,
    Asset('TAI'): A_USDT,
    Asset('YFL'): A_USDT,
    Asset('TRUMPWIN'): A_USDT,
    Asset('TRUMPLOSE'): A_USDT,
    Asset('KLV'): A_USDT,
    Asset('KRT'): Asset('KRW'),
    Asset('RVC'): A_USDT,
    Asset('SDT'): A_USDT,
    Asset('CHI'): A_USDT,
    Asset('BAKE'): Asset('BNB'),
    Asset('BURGER'): Asset('BNB'),
    Asset('CAKE'): Asset('BNB'),
    Asset('BREE'): A_USDT,
    Asset('GHST'): A_USDT,
    Asset('MEXP'): A_USDT,
    Asset('POLS'): A_USDT,
    Asset('RARI'): A_USDT,
    Asset('VALUE'): A_USDT,
    Asset('$BASED'): A_WETH,
    Asset('DPI'): A_WETH,
    Asset('JRT'): A_USDT,
    Asset('PICKLE'): A_USDT,
    Asset('FILDOWN'): A_USDT,
    Asset('FILUP'): A_USDT,
    Asset('YFIDOWN'): A_USDT,
    Asset('YFIUP'): A_USDT,
    Asset('BOT'): A_USDT,
    Asset('SG'): A_USDT,
    Asset('SPARTA'): Asset('BNB'),
    Asset('MIR'): Asset('USDC'),
    Asset('NDX'): A_WETH,
}
CRYPTOCOMPARE_SPECIAL_CASES = CRYPTOCOMPARE_SPECIAL_CASES_MAPPING.keys()
CRYPTOCOMPARE_HOURQUERYLIMIT = 2000

METADATA_RE = re.compile('.*"start_time": *(.*), *"end_time": *(.*), "data".*')


class PriceHistoryEntry(NamedTuple):
    time: Timestamp
    low: Price
    high: Price


class PriceHistoryData(NamedTuple):
    data: List[PriceHistoryEntry]
    start_time: Timestamp
    end_time: Timestamp


class HistoHourAssetData(NamedTuple):
    timestamp: Timestamp
    usd_price: Price


# Safest starting timestamp for requesting an asset price via histohour avoiding
# 0 price. Be aware `usd_price` is from the 'close' price in USD.
CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES: Dict[Asset, HistoHourAssetData] = {
    A_COMP: HistoHourAssetData(
        timestamp=Timestamp(1592629200),
        usd_price=Price(FVal('239.13')),
    ),
}


def _dict_history_to_entries(data: List[Dict[str, Any]]) -> List[PriceHistoryEntry]:
    """Turns a list of dict of history entries to a list of proper objects"""
    return [
        PriceHistoryEntry(
            time=Timestamp(entry['time']),
            low=Price(FVal(entry['low'])),
            high=Price(FVal(entry['high'])),
        ) for entry in data
    ]


def _dict_history_to_data(data: Dict[str, Any]) -> PriceHistoryData:
    """Turns a price history data dict entry into a proper object"""
    return PriceHistoryData(
        data=_dict_history_to_entries(data['data']),
        start_time=Timestamp(data['start_time']),
        end_time=Timestamp(data['end_time']),
    )


def _multiply_str_nums(a: str, b: str) -> str:
    """Multiplies two string numbers and returns the result as a string"""
    return str(FVal(a) * FVal(b))


def pairwise(iterable: Iterable[Any]) -> Iterator:
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


def _check_hourly_data_sanity(
        data: List[Dict[str, Any]],
        from_asset: Asset,
        to_asset: Asset,
) -> None:
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.

    If not then a RemoteError is raised
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['time'] - n1['time']
        if diff != 3600:
            raise RemoteError(
                'Unexpected data format in cryptocompare query_endpoint_histohour. '
                "Problem at indices {} and {} of {}_to_{} prices. Time difference is: {}".format(
                    index, index + 1, from_asset.symbol, to_asset.symbol, diff),
            )

        index += 2


def _get_cache_key(from_asset: Asset, to_asset: Asset) -> Optional[PairCacheKey]:
    try:
        from_cc_asset = from_asset.to_cryptocompare()
        to_cc_asset = to_asset.to_cryptocompare()
    except UnsupportedAsset:
        return None

    return PairCacheKey(from_cc_asset + '_' + to_cc_asset)


def _write_history_data_in_file(
        data: List[Dict[str, Any]],
        filepath: Path,
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> None:
    log.info(
        'Writing history file',
        filepath=filepath,
        start_time=start_ts,
        end_time=end_ts,
    )
    with open(filepath, 'w') as outfile:
        history_dict: Dict[str, Any] = {}
        # From python 3.5 dict order should be preserved so we can expect
        # start and end time to come before the data in the file
        history_dict['start_time'] = start_ts
        history_dict['end_time'] = end_ts
        history_dict['data'] = data
        outfile.write(rlk_jsondumps(history_dict))


class Cryptocompare(ExternalServiceWithApiKey):
    def __init__(self, data_directory: Path, database: Optional['DBHandler']) -> None:
        super().__init__(database=database, service_name=ExternalService.CRYPTOCOMPARE)
        self.data_directory = data_directory
        self.price_history: Dict[PairCacheKey, PriceHistoryData] = {}
        self.price_history_file: Dict[PairCacheKey, Path] = {}
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.last_histohour_query_ts = 0
        self.last_rate_limit = 0

        price_history_dir = get_or_make_price_history_dir(data_directory)
        # Check the data folder and remember the filenames of any cached history
        prefix = os.path.join(str(price_history_dir), PRICE_HISTORY_FILE_PREFIX)
        prefix = prefix.replace('\\', '\\\\')
        regex = re.compile(prefix + r'(.*)\.json')

        for file_ in price_history_dir.rglob(PRICE_HISTORY_FILE_PREFIX + '*.json'):
            file_str = str(file_).replace('\\\\', '\\')
            match = regex.match(file_str)
            assert match
            cache_key = PairCacheKey(match.group(1))
            self.price_history_file[cache_key] = file_

    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int = CRYPTOCOMPARE_RATE_LIMIT_WAIT_TIME,
    ) -> bool:
        """Checks if it's okay to query cryptocompare historical price. This is determined by:

        - Existence of a cached price
        - Last rate limit
        """
        cached_data = self._got_cached_data_at_timestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        rate_limited = self.rate_limited_in_last(seconds)
        can_query = cached_data is not None or not rate_limited
        logger.debug(
            f'{"Will" if can_query else "Will not"} query '
            f'Cryptocompare history for {from_asset.identifier} -> '
            f'{to_asset.identifier} @ {timestamp}. Cached data: {cached_data is not None}'
            f' rate_limited in last {seconds} seconds: {rate_limited}',
        )
        return can_query

    def rate_limited_in_last(self, seconds: int = CRYPTOCOMPARE_RATE_LIMIT_WAIT_TIME) -> bool:
        """Checks when we were last rate limited by CC and if it was within the given seconds"""
        return ts_now() - self.last_rate_limit <= seconds

    def set_database(self, database: 'DBHandler') -> None:
        """If the cryptocompare instance was initialized without a DB this sets its DB"""
        msg = 'set_database was called on a cryptocompare instance that already has a DB'
        assert self.db is None, msg
        self.db = database

    def unset_database(self) -> None:
        """Remove the database connection from this cryptocompare instance

        This should happen when a user logs out"""
        msg = 'unset_database was called on a cryptocompare instance that has no DB'
        assert self.db is not None, msg
        self.db = None

    def _api_query(self, path: str) -> Dict[str, Any]:
        """Queries cryptocompare

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        querystr = f'https://min-api.cryptocompare.com/data/{path}'
        log.debug('Querying cryptocompare', url=querystr)
        api_key = self._get_api_key()
        if api_key:
            querystr += '?' if '?' not in querystr else '&'
            querystr += f'api_key={api_key}'

        tries = CRYPTOCOMPARE_QUERY_RETRY_TIMES
        while tries >= 0:
            try:
                response = self.session.get(querystr)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Cryptocompare API request failed due to {str(e)}') from e

            try:
                json_ret = rlk_jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Cryptocompare returned invalid JSON response: {response.text}',
                ) from e

            try:
                # backoff and retry 3 times =  1 + 1.5 + 3 = at most 5.5 secs
                # Failing is also fine, since all calls have secondary data sources
                # for example coingecko
                if json_ret.get('Message', None) == RATE_LIMIT_MSG:
                    self.last_rate_limit = ts_now()
                    if tries >= 1:
                        backoff_seconds = 3 / tries
                        log.debug(
                            f'Got rate limited by cryptocompare. '
                            f'Backing off for {backoff_seconds}',
                        )
                        gevent.sleep(backoff_seconds)
                        tries -= 1
                        continue

                    # else
                    log.debug(
                        f'Got rate limited by cryptocompare and did not manage to get a '
                        f'request through even after {CRYPTOCOMPARE_QUERY_RETRY_TIMES} '
                        f'incremental backoff retries',
                    )

                if json_ret.get('Response', 'Success') != 'Success':
                    error_message = f'Failed to query cryptocompare for: "{querystr}"'
                    if 'Message' in json_ret:
                        error_message += f'. Error: {json_ret["Message"]}'

                    log.warning(
                        'Cryptocompare query failure',
                        url=querystr,
                        error=error_message,
                        status_code=response.status_code,
                    )
                    raise RemoteError(error_message)

                return json_ret['Data'] if 'Data' in json_ret else json_ret
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of Cryptocompare json_response. '
                    f'Missing key entry for {str(e)}',
                ) from e

        raise AssertionError('We should never get here')

    def _special_case_handling(
            self,
            method_name: Literal[
                'query_endpoint_histohour',
                'query_current_price',
                'query_endpoint_pricehistorical',
            ],
            from_asset: Asset,
            to_asset: Asset,
            **kwargs: Any,
    ) -> Any:
        """Special case handling for queries that need combination of multiple asset queries

        This is hopefully temporary and can be taken care of by cryptocompare itself in the future.

        For some assets cryptocompare can only figure out the price via intermediaries.
        This function takes care of these special cases."""
        method = getattr(self, method_name)
        intermediate_asset = CRYPTOCOMPARE_SPECIAL_CASES_MAPPING[from_asset]
        result1 = method(
            from_asset=from_asset,
            to_asset=intermediate_asset,
            handling_special_case=True,
            **kwargs,
        )
        result2 = method(
            from_asset=intermediate_asset,
            to_asset=to_asset,
            handling_special_case=True,
            **kwargs,
        )
        result: Any
        if method_name == 'query_endpoint_histohour':
            result = {
                'Aggregated': result1['Aggregated'],
                'TimeFrom': result1['TimeFrom'],
                'TimeTo': result1['TimeTo'],
            }
            result1 = result1['Data']
            result2 = result2['Data']
            data = []
            for idx, entry in enumerate(result1):
                entry2 = result2[idx]
                data.append({
                    'time': entry['time'],
                    'high': _multiply_str_nums(entry['high'], entry2['high']),
                    'low': _multiply_str_nums(entry['low'], entry2['low']),
                    'open': _multiply_str_nums(entry['open'], entry2['open']),
                    'volumefrom': entry['volumefrom'],
                    'volumeto': entry['volumeto'],
                    'close': _multiply_str_nums(entry['close'], entry2['close']),
                    'conversionType': entry['conversionType'],
                    'conversionSymbol': entry['conversionSymbol'],
                })
            result['Data'] = data
            return result

        if method_name in ('query_current_price', 'query_endpoint_pricehistorical'):
            return result1 * result2

        raise RuntimeError(f'Illegal method_name: {method_name}. Should never happen')

    def query_endpoint_histohour(
            self,
            from_asset: Asset,
            to_asset: Asset,
            limit: int,
            to_timestamp: Timestamp,
            handling_special_case: bool = False,
    ) -> Dict[str, Any]:
        """Returns the full histohour response including TimeFrom and TimeTo

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        - May raise PriceQueryUnsupportedAsset if from/to assets are not known to cryptocompare
        """
        special_asset = (
            from_asset in CRYPTOCOMPARE_SPECIAL_CASES or to_asset in CRYPTOCOMPARE_SPECIAL_CASES
        )
        if special_asset and not handling_special_case:
            return self._special_case_handling(
                method_name='query_endpoint_histohour',
                from_asset=from_asset,
                to_asset=to_asset,
                limit=limit,
                to_timestamp=to_timestamp,
            )

        try:
            cc_from_asset_symbol = from_asset.to_cryptocompare()
            cc_to_asset_symbol = to_asset.to_cryptocompare()
        except UnsupportedAsset as e:
            raise PriceQueryUnsupportedAsset(e.asset_name) from e

        query_path = (
            f'v2/histohour?fsym={cc_from_asset_symbol}&tsym={cc_to_asset_symbol}'
            f'&limit={limit}&toTs={to_timestamp}'
        )
        result = self._api_query(path=query_path)
        return result

    def query_current_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            handling_special_case: bool = False,
    ) -> Price:
        """Returns the current price of an asset compared to another asset

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        - May raise PriceQueryUnsupportedAsset if from/to assets are not known to cryptocompare
        """
        special_asset = (
            from_asset in CRYPTOCOMPARE_SPECIAL_CASES or to_asset in CRYPTOCOMPARE_SPECIAL_CASES
        )
        if special_asset and not handling_special_case:
            return self._special_case_handling(
                method_name='query_current_price',
                from_asset=from_asset,
                to_asset=to_asset,
            )
        try:
            cc_from_asset_symbol = from_asset.to_cryptocompare()
            cc_to_asset_symbol = to_asset.to_cryptocompare()
        except UnsupportedAsset as e:
            raise PriceQueryUnsupportedAsset(e.asset_name) from e

        query_path = f'price?fsym={cc_from_asset_symbol}&tsyms={cc_to_asset_symbol}'
        result = self._api_query(path=query_path)
        # Up until 23/09/2020 cryptocompare may return {} due to bug.
        # Handle that case by assuming 0 if that happens
        if cc_to_asset_symbol not in result:
            return Price(ZERO)

        return Price(FVal(result[cc_to_asset_symbol]))

    def query_endpoint_pricehistorical(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            handling_special_case: bool = False,
    ) -> Price:
        """Queries the historical daily price of from_asset to to_asset for timestamp

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        - May raise PriceQueryUnsupportedAsset if from/to assets are not known to cryptocompare
        """
        log.debug(
            'Querying cryptocompare for daily historical price',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        special_asset = (
            from_asset in CRYPTOCOMPARE_SPECIAL_CASES or to_asset in CRYPTOCOMPARE_SPECIAL_CASES
        )
        if special_asset and not handling_special_case:
            return self._special_case_handling(
                method_name='query_endpoint_pricehistorical',
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
            )

        try:
            cc_from_asset_symbol = from_asset.to_cryptocompare()
            cc_to_asset_symbol = to_asset.to_cryptocompare()
        except UnsupportedAsset as e:
            raise PriceQueryUnsupportedAsset(e.asset_name) from e

        query_path = (
            f'pricehistorical?fsym={cc_from_asset_symbol}&tsyms={cc_to_asset_symbol}'
            f'&ts={timestamp}'
        )
        if to_asset == 'BTC':
            query_path += '&tryConversion=false'
        result = self._api_query(query_path)
        # Up until 23/09/2020 cryptocompare may return {} due to bug.
        # Handle that case by assuming 0 if that happens
        if (
            cc_from_asset_symbol not in result or
            cc_to_asset_symbol not in result[cc_from_asset_symbol]
        ):
            return Price(ZERO)

        return Price(FVal(result[cc_from_asset_symbol][cc_to_asset_symbol]))

    def get_cached_data(self, from_asset: Asset, to_asset: Asset) -> Optional[PriceHistoryData]:
        """Get the cached data for a pair if they exist. This reads the entire file,
        gets the metadata, and the data itself, and loops through it to convert it
        to our own data structure.

        It can be rather slow for big files.
        """
        cache_key = _get_cache_key(from_asset=from_asset, to_asset=to_asset)
        if cache_key is None or cache_key not in self.price_history_file:
            return None

        if cache_key not in self.price_history:
            try:
                with open(self.price_history_file[cache_key], 'r') as f:
                    data = rlk_jsonloads_dict(f.read())
                    self.price_history[cache_key] = _dict_history_to_data(data)
            except (OSError, JSONDecodeError):
                return None

        return self.price_history[cache_key]

    def _read_cachefile_metadata(
            self,
            cache_key: PairCacheKey,
    ) -> Optional[Tuple[Timestamp, Timestamp]]:
        """Read only the start of the json file and get start/end time

        MUCH faster than reading the entire file, since these files can become hundreds of MBs
        """
        try:
            with open(self.price_history_file[cache_key], 'r') as f:
                f.seek(0)
                data = f.read(100)  # first 100 bytes, should contain the data
        except OSError:
            return None

        match = METADATA_RE.match(data)
        if not match:
            return None
        result = match.group(1, 2)
        if any(x is None for x in result):
            return None

        try:
            start_ts = Timestamp(int(result[0]))
            end_ts = Timestamp(int(result[1]))
        except ValueError:
            return None

        return start_ts, end_ts

    def get_cached_data_metadata(
            self,
            from_asset: Asset,
            to_asset: Asset,
    ) -> Optional[Tuple[Timestamp, Timestamp]]:
        """Get the cached data metadata for a pair if they exist.
        This reads only the start of the json file to get the metadata.

        Should be a faster way that get_cached_data to check if a cache exists and
        get only its metadata. start and end time.
        """
        cache_key = _get_cache_key(from_asset=from_asset, to_asset=to_asset)
        if cache_key is None or cache_key not in self.price_history_file:
            return None

        memcache = self.price_history.get(cache_key, None)
        if memcache is not None:
            return memcache.start_time, memcache.end_time

        return self._read_cachefile_metadata(cache_key)

    def _got_cached_data_at_timestamp(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Optional[PriceHistoryData]:
        """Check if we got a price history for the timestamp cached"""
        data = self.get_cached_data(from_asset, to_asset)
        if data is not None and data.start_time <= timestamp < data.end_time:
            return data

        return None

    @staticmethod
    def _retrieve_price_from_data(
            data: Optional[List[PriceHistoryEntry]],
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """Reads historical price data list returned from cryptocompare histohour
        or cache and returns a price.

        If nothing is found it returns Price(0). This can also happen if cryptocompare
        returns a list of 0s for the timerange.
        """
        price = Price(ZERO)
        if data is None or len(data) == 0:
            return price

        # all data are sorted and timestamps are always increasing by 1 hour
        # find the closest entry to the provided timestamp
        if timestamp >= data[0].time:
            index_in_bounds = True
            # convert_to_int can't raise here due to its input
            index = convert_to_int((timestamp - data[0].time) / 3600, accept_only_exact=False)
            if index > len(data) - 1:  # index out of bounds
                # Try to see if index - 1 is there and if yes take it
                if index > len(data):
                    index = index - 1
                else:  # give up. This happened: https://github.com/rotki/rotki/issues/1534
                    log.error(
                        f'Expected data index in cryptocompare historical hour price '
                        f'not found. Queried price of: {from_asset.identifier} in '
                        f'{to_asset.identifier} at {timestamp}. Data '
                        f'index: {index}. Length of returned data: {len(data)}. '
                        f'https://github.com/rotki/rotki/issues/1534. Attempting other methods...',
                    )
                    index_in_bounds = False

            if index_in_bounds:
                diff = abs(data[index].time - timestamp)
                if index + 1 <= len(data) - 1:
                    diff_p1 = abs(data[index + 1].time - timestamp)
                    if diff_p1 < diff:
                        index = index + 1

                if data[index].high is not None and data[index].low is not None:
                    price = Price((data[index].high + data[index].low) / 2)

        else:
            # no price found in the historical data from/to asset, try alternatives
            price = Price(ZERO)

        return price

    def _get_histohour_data_for_range(
            self,
            from_asset: Asset,
            to_asset: Asset,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> Deque[Dict[str, Any]]:
        """Query histohour data from cryptocompare for a time range going backwards in time

        Will stop when to_timestamp is reached OR when no more prices are returned

        Returns a list of histohour entries with increasing timestamp. Starting from
        to_timestamp (or higher) if no data and ending in from_timestamp or lower, if no data

        May raise:
        - RemoteError if there is problems with the query
        """
        msg = '_get_histohour_data_for_range from_timestamp should be bigger than to_timestamp'
        assert from_timestamp >= to_timestamp, msg

        calculated_history: Deque[Dict[str, Any]] = deque()
        end_date = from_timestamp
        while True:
            log.debug(
                'Querying cryptocompare for hourly historical price',
                from_asset=from_asset,
                to_asset=to_asset,
                cryptocompare_hourquerylimit=CRYPTOCOMPARE_HOURQUERYLIMIT,
                end_date=end_date,
            )
            resp = self.query_endpoint_histohour(
                from_asset=from_asset,
                to_asset=to_asset,
                limit=2000,
                to_timestamp=end_date,
            )
            if all(FVal(x['close']) == ZERO for x in resp['Data']):
                # all prices zero Means we have reached the end of available prices
                break

            end_date = Timestamp(end_date - (CRYPTOCOMPARE_HOURQUERYLIMIT * 3600))
            if end_date != resp['TimeFrom']:
                # If we get more than we needed, since we are close to the now_ts
                # then skip all the already included entries
                diff = abs(end_date - resp['TimeFrom'])
                # If the start date has less than 3600 secs difference from previous
                # end date then do nothing. If it has more skip all already included entries
                if diff >= 3600:
                    if resp['Data'][diff // 3600]['time'] != end_date:
                        raise RemoteError(
                            'Unexpected data format in cryptocompare query_endpoint_histohour. '
                            'Expected to find the previous date timestamp during '
                            'cryptocompare historical data fetching',
                        )
                    # just add only the part from the previous timestamp and on
                    resp['Data'] = resp['Data'][diff // 3600:]

            # If last time slot and first new are the same, skip the first new slot
            last_entry_equal_to_first = (
                len(calculated_history) != 0 and
                calculated_history[0]['time'] == resp['Data'][-1]['time']
            )
            if last_entry_equal_to_first:
                resp['Data'] = resp['Data'][:-1]
            if len(calculated_history) != 0:
                calculated_history.extendleft(reversed(resp['Data']))
            else:
                calculated_history = deque(resp['Data'])

            if end_date - to_timestamp <= 3600:
                # Ending the loop query. Also pop any extra timestamps
                while (
                        len(calculated_history) != 0 and
                        calculated_history[0]['time'] <= to_timestamp
                ):
                    calculated_history.popleft()
                break

        return calculated_history

    def get_all_cache_data(self) -> List[Dict[str, Any]]:
        """Returns all current cryptocompare cache data

        Note: The return asset identifiers are the cryptocompare ones and not
        the canonical ones
        """
        cache_data = []
        for cache_key in self.price_history_file:
            memcache = self.price_history.get(cache_key, None)
            if memcache:
                from_timestamp = memcache.start_time
                to_timestamp = memcache.end_time
            else:
                metadata = self._read_cachefile_metadata(cache_key)
                if metadata is None:
                    continue
                from_timestamp, to_timestamp = metadata

            # cache key has to be valid here. Also note that the assets are
            from_asset, to_asset = cache_key.split('_')
            cache_data.append({
                'from_asset': from_asset,
                'to_asset': to_asset,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
            })

        return cache_data

    def delete_cache(self, from_asset: Asset, to_asset: Asset) -> None:
        """Deletes a cache if it exists. Does nothing if it does not"""
        cache_key = _get_cache_key(from_asset=from_asset, to_asset=to_asset)
        if cache_key is None:
            return

        self.price_history.pop(cache_key, None)
        filename = self.price_history_file.get(cache_key, None)
        if filename:
            try:
                filename.unlink()
            except FileNotFoundError:  # TODO: In python 3.8 we can add missing_ok=True to unlink  # noqa: E501
                pass

    def create_cache(
            self,
            from_asset: Asset,
            to_asset: Asset,
            purge_old: bool,
    ) -> None:
        """Creates the cache of the given asset pair from the start of time
        until now

        if purge_old is true then any old cache in memory and in a file is purged

        May raise:
            - RemoteError if there is a problem reaching cryptocompare
            - UnsupportedAsset if any of the two assets is not supported by cryptocompare
        """
        now = ts_now()

        # If we got cached data for up to 1 hour ago there is no point doing anything
        cached_data = self._got_cached_data_at_timestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=Timestamp(now - 3600),
        )
        if cached_data and not purge_old:
            log.debug(
                'Did not create new cache since we got cache until 1 hour ago',
                from_asset=from_asset,
                to_asset=to_asset,
            )
            return

        if purge_old:
            cache_key = _get_cache_key(from_asset=from_asset, to_asset=to_asset)
            if cache_key and cache_key in self.price_history_file:
                filename = self.price_history_file[cache_key]
                self.price_history.pop(cache_key, None)
                try:
                    filename.unlink()
                except FileNotFoundError:  # TODO: In python 3.8 we can add missing_ok=True to unlink  # noqa: E501
                    pass

        self.get_historical_data(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=now,
            only_check_cache=False,
        )

    def get_historical_data(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            only_check_cache: bool,
    ) -> Optional[List[PriceHistoryEntry]]:
        """
        Get historical hour price data from cryptocompare

        Returns a sorted list of price entries.

        If only_check_cache is True then if the data is not cached locally this will return None

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        - May raise UnsupportedAsset if from/to asset is not supported by cryptocompare
        """
        log.debug(
            'Retrieving historical price data from cryptocompare',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        cached_data = self._got_cached_data_at_timestamp(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if cached_data is not None:
            return cached_data.data

        if only_check_cache:
            return None

        cache_key = _get_cache_key(from_asset=from_asset, to_asset=to_asset)
        if cache_key is None:
            return None

        now_ts = ts_now()
        # save time at start of the query, in case the query does not complete due to rate limit
        self.last_histohour_query_ts = now_ts
        if cache_key in self.price_history:
            old_data = self.price_history[cache_key].data
            transformed_old_data = deque([x._asdict() for x in old_data])
            if timestamp > self.price_history[cache_key].end_time:
                # We have a cache but the requested timestamp does not hit it
                new_data = self._get_histohour_data_for_range(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    from_timestamp=now_ts,
                    to_timestamp=self.price_history[cache_key].end_time,
                )
                if len(new_data) == 0:
                    new_history = transformed_old_data
                else:
                    if len(old_data) != 0 and old_data[-1].time == new_data[0]['time']:
                        transformed_old_data.pop()
                    new_history = transformed_old_data + new_data

            else:
                # only other possibility, timestamp < cached start_time
                # Get all available data, even before to_timestamp
                new_data = self._get_histohour_data_for_range(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    from_timestamp=self.price_history[cache_key].start_time,
                    to_timestamp=Timestamp(0),
                )
                if len(new_data) == 0:
                    new_history = transformed_old_data
                else:
                    if len(old_data) != 0 and new_data[-1]['time'] == old_data[0].time:
                        new_data.pop()
                    new_history = new_data + transformed_old_data

            calculated_history = list(new_history)

        else:
            calculated_history = list(self._get_histohour_data_for_range(
                from_asset=from_asset,
                to_asset=to_asset,
                from_timestamp=now_ts,
                to_timestamp=Timestamp(0),
            ))

        if len(calculated_history) == 0:
            return []  # empty list means we found nothing

        # Let's always check for data sanity for the hourly prices.
        _check_hourly_data_sanity(calculated_history, from_asset, to_asset)
        # and now since we actually queried the data let's also cache them
        filename = (
            get_or_make_price_history_dir(self.data_directory) /
            (PRICE_HISTORY_FILE_PREFIX + cache_key + '.json')
        )
        log.info(
            'Updating price history cache',
            filename=filename,
            from_asset=from_asset,
            to_asset=to_asset,
        )
        _write_history_data_in_file(
            data=calculated_history,
            filepath=filename,
            start_ts=calculated_history[0]['time'],
            end_ts=now_ts,
        )

        # Finally save the objects in memory and return them
        data_including_time = {
            'data': calculated_history,
            'start_time': calculated_history[0]['time'],
            'end_time': now_ts,
        }
        self.price_history_file[cache_key] = filename
        self.price_history[cache_key] = _dict_history_to_data(data_including_time)
        self.last_histohour_query_ts = ts_now()  # also save when last query finished
        return self.price_history[cache_key].data

    @staticmethod
    def _check_and_get_special_histohour_price(
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """For the given timestamp, check whether the from..to asset price
        (or viceversa) is a special histohour API case. If so, return the price
        based on the assets pair, otherwise return zero.

        NB: special histohour API cases are the ones where this Cryptocompare
        API returns zero prices per hour.
        """
        price = Price(ZERO)
        if (
            from_asset in CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES and to_asset == A_USD or
            from_asset == A_USD and to_asset in CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES
        ):
            asset_data = (
                CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES[from_asset]
                if to_asset == A_USD
                else CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES[to_asset]
            )
            if timestamp <= asset_data.timestamp:
                price = (
                    asset_data.usd_price
                    if to_asset == A_USD
                    else Price(FVal('1') / asset_data.usd_price)
                )
                log.warning(
                    f'Query price of: {from_asset.identifier} in {to_asset.identifier} '
                    f'at timestamp {timestamp} may return zero price. '
                    f'Setting price to {price}, from timestamp {asset_data.timestamp}.',
                )
        return price

    def query_historical_price(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> Price:
        """
        Query the historical price on `timestamp` for `from_asset` in `to_asset`.
        So how much `to_asset` does 1 unit of `from_asset` cost.

        This tries to:
        1. Find cached cryptocompare values and return them
        2. If none exist at the moment try the normal historical price endpoint
        3. Else fail

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is known to miss from cryptocompare
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        # NB: check if the from..to asset price (or viceversa) is a special
        # histohour API case.
        price = self._check_and_get_special_histohour_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if price != Price(ZERO):
            return price

        try:
            data = self.get_historical_data(
                from_asset=from_asset,
                to_asset=to_asset,
                timestamp=timestamp,
                only_check_cache=True,
            )
        except UnsupportedAsset as e:
            raise PriceQueryUnsupportedAsset(e.asset_name) from e

        price = self._retrieve_price_from_data(
            data=data,
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if price == Price(ZERO):
            log.debug(
                f"Couldn't find historical price from {from_asset} to "
                f"{to_asset} at timestamp {timestamp} through cryptocompare."
                f" Attempting to get daily price...",
            )
            price = self.query_endpoint_pricehistorical(from_asset, to_asset, timestamp)

        if price == Price(ZERO):
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                date=timestamp_to_date(
                    timestamp,
                    formatstr='%d/%m/%Y, %H:%M:%S',
                    treat_as_local=True,
                ),
            )

        log.debug(
            'Got historical price from cryptocompare',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            price=price,
        )

        return price

    def all_coins(self) -> Dict[str, Any]:
        """
        Gets the list of all the cryptocompare coins

        May raise:
        - RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        # Get coin list of cryptocompare
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cryptocompare_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found cryptocompare coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'r') as f:
                try:
                    data = rlk_jsonloads_dict(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery cryptocompare
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Cryptocompare coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._api_query('all/coinlist')

            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        # As described in the docs
        # https://min-api.cryptocompare.com/documentation?key=Other&cat=allCoinsWithContentEndpoint
        # This is not the entire list of assets in the system, so I am manually adding
        # here assets I am aware of that they already have historical data for in thei
        # cryptocompare system
        data['DAO'] = object()
        data['USDT'] = object()
        data['VEN'] = object()
        data['AIR*'] = object()  # This is Aircoin
        # This is SpendCoin (https://coinmarketcap.com/currencies/spendcoin/)
        data['SPND'] = object()
        # This is eBitcoinCash (https://coinmarketcap.com/currencies/ebitcoin-cash/)
        data['EBCH'] = object()
        # This is Educare (https://coinmarketcap.com/currencies/educare/)
        data['EKT'] = object()
        # This is Knoxstertoken (https://coinmarketcap.com/currencies/knoxstertoken/)
        data['FKX'] = object()
        # This is FNKOS (https://coinmarketcap.com/currencies/fnkos/)
        data['FNKOS'] = object()
        # This is FansTime (https://coinmarketcap.com/currencies/fanstime/)
        data['FTI'] = object()
        # This is Gene Source Code Chain
        # (https://coinmarketcap.com/currencies/gene-source-code-chain/)
        data['GENE*'] = object()
        # This is GazeCoin (https://coinmarketcap.com/currencies/gazecoin/)
        data['GZE'] = object()
        # This is probaly HarmonyCoin (https://coinmarketcap.com/currencies/harmonycoin-hmc/)
        data['HMC*'] = object()
        # This is IoTChain (https://coinmarketcap.com/currencies/iot-chain/)
        data['ITC'] = object()
        # This is Luna Coin (https://coinmarketcap.com/currencies/luna-coin/)
        data['LUNA'] = object
        # This is MFTU (https://coinmarketcap.com/currencies/mainstream-for-the-underground/)
        data['MFTU'] = object()
        # This is Nexxus (https://coinmarketcap.com/currencies/nexxus/)
        data['NXX'] = object()
        # This is Owndata (https://coinmarketcap.com/currencies/owndata/)
        data['OWN'] = object()
        # This is PiplCoin (https://coinmarketcap.com/currencies/piplcoin/)
        data['PIPL'] = object()
        # This is PKG Token (https://coinmarketcap.com/currencies/pkg-token/)
        data['PKG'] = object()
        # This is Quibitica https://coinmarketcap.com/currencies/qubitica/
        data['QBIT'] = object()
        # This is DPRating https://coinmarketcap.com/currencies/dprating/
        data['RATING'] = object()
        # This is RocketPool https://coinmarketcap.com/currencies/rocket-pool/
        data['RPL'] = object()
        # This is SpeedMiningService (https://coinmarketcap.com/currencies/speed-mining-service/)
        data['SMS'] = object()
        # This is SmartShare (https://coinmarketcap.com/currencies/smartshare/)
        data['SSP'] = object()
        # This is ThoreCoin (https://coinmarketcap.com/currencies/thorecoin/)
        data['THR'] = object()
        # This is Transcodium (https://coinmarketcap.com/currencies/transcodium/)
        data['TNS'] = object()

        return data
