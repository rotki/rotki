import logging
import os
from collections import deque
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, Dict, Iterable, Iterator, List, NamedTuple, Optional

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_BAT,
    A_BNB,
    A_BZRX,
    A_CBAT,
    A_CDAI,
    A_COMP,
    A_CREP,
    A_CUSDC,
    A_CUSDT,
    A_CWBTC,
    A_CZRX,
    A_DAI,
    A_DPI,
    A_KRW,
    A_MCB,
    A_REP,
    A_SAI,
    A_STAKE,
    A_UNI,
    A_USD,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_WETH,
    A_YFII,
    A_ZRX,
)
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import (
    DeserializationError,
    NoPriceForGivenTimestamp,
    PriceQueryUnsupportedAsset,
    RemoteError,
    UnsupportedAsset,
)
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date, ts_now
from rotkehlchen.utils.serialization import jsonloads_dict, rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


RATE_LIMIT_MSG = 'You are over your rate limit please upgrade your account!'
CRYPTOCOMPARE_QUERY_RETRY_TIMES = 3
CRYPTOCOMPARE_RATE_LIMIT_WAIT_TIME = 60
CRYPTOCOMPARE_SPECIAL_CASES_MAPPING = {
    'ADADOWN': A_USDT,
    'ADAUP': A_USDT,
    'BNBDOWN': A_USDT,
    'BNBUP': A_USDT,
    'BTCDOWN': A_USDT,
    'BTCUP': A_USDT,
    'ETHDOWN': A_USDT,
    'ETHUP': A_USDT,
    'EOSDOWN': A_USDT,
    'EOSUP': A_USDT,
    'DOTDOWN': A_USDT,
    'DOTUP': A_USDT,
    'LTCDOWN': A_USDT,
    'LTCUP': A_USDT,
    'TRXDOWN': A_USDT,
    'TRXUP': A_USDT,
    'XRPDOWN': A_USDT,
    'XRPUP': A_USDT,
    'LINKDOWN': A_USDT,
    'LINKUP': A_USDT,
    'XTZDOWN': A_USDT,
    'XTZUP': A_USDT,
    'ANK': A_USDT,
    'CORN': A_USDT,
    'SAL': A_USDT,
    'CRT': A_USDT,
    'JFI': A_USDT,
    'PEARL': A_USDT,
    'TAI': A_USDT,
    'KLV': A_USDT,
    'KRT': A_KRW,
    'RVC': A_USDT,
    'SDT': A_USDT,
    'BAKE': A_BNB,
    'BURGER': A_BNB,
    'CAKE': A_BNB,
    'FILDOWN': A_USDT,
    'FILUP': A_USDT,
    'YFIDOWN': A_USDT,
    'YFIUP': A_USDT,
    'SPARTA': A_BNB,
    strethaddress_to_identifier('0x679131F591B4f369acB8cd8c51E68596806c3916'): A_WETH,  # Trustlines  # noqa: E501
    strethaddress_to_identifier('0xf8aD7dFe656188A23e89da09506Adf7ad9290D5d'): A_USDT,  # Blocery
    A_CDAI: A_DAI,  # Compound DAI
    strethaddress_to_identifier('0x70e36f6BF80a52b3B46b3aF8e106CC0ed743E8e4'): A_COMP,  # Compound Comp  # noqa: E501
    A_CBAT: A_BAT,  # Comppound BAT
    A_CREP: A_REP,  # Compound REP
    strethaddress_to_identifier('0xF5DCe57282A584D2746FaF1593d3121Fcac444dC'): A_SAI,  # Compound SAI  # noqa: E501
    A_CUSDC: A_USDC,  # Compound USDC
    A_CUSDT: A_USDT,  # Compound USDT
    A_CWBTC: A_WBTC,  # Compound WBTC
    strethaddress_to_identifier('0x35A18000230DA775CAc24873d00Ff85BccdeD550'): A_UNI,  # Compound UNI  # noqa: E501
    A_CZRX: A_ZRX,  # Compound ZRX
    strethaddress_to_identifier('0x26CE25148832C04f3d7F26F32478a9fe55197166'): A_USDT,  # DEXTools
    strethaddress_to_identifier('0x0A913beaD80F321E7Ac35285Ee10d9d922659cB7'): A_USDT,  # DOS Network token  # noqa: E501
    strethaddress_to_identifier('0x6B9f031D718dDed0d681c20cB754F97b3BB81b78'): A_USDT,  # GEEQ
    A_STAKE: A_USDT,  # xDAI STAKE
    A_MCB: A_USDT,  # MCDEX Token
    strethaddress_to_identifier('0x0Ba45A8b5d5575935B8158a88C631E9F9C95a2e5'): A_USDT,  # Tellor Tributes  # noqa: E501
    strethaddress_to_identifier('0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e'): A_USDT,  # YFI
    strethaddress_to_identifier('0x0AaCfbeC6a24756c20D41914F2caba817C0d8521'): A_USDT,  # YAM
    strethaddress_to_identifier('0x30f271C9E86D2B7d00a6376Cd96A1cFBD5F0b9b3'): A_USDT,  # Decentr
    strethaddress_to_identifier('0x0258F474786DdFd37ABCE6df6BBb1Dd5dfC4434a'): A_USDT,  # Orion protocol  # noqa: E501
    strethaddress_to_identifier('0x3C6ff50c9Ec362efa359317009428d52115fe643'): A_USDT,  # PeerEx Network  # noqa: E501
    strethaddress_to_identifier('0xFE2786D7D1cCAb8B015f6Ef7392F67d778f8d8D7'): A_USDT,  # Parsiq Token  # noqa: E501
    strethaddress_to_identifier('0x9469D013805bFfB7D3DEBe5E7839237e535ec483'): A_USDT,  # Darwinia Network  # noqa: E501
    strethaddress_to_identifier('0x25377ddb16c79C93B0CBf46809C8dE8765f03FCd'): A_USDT,  # Synthetic CBDAO  # noqa: E501
    A_YFII: A_USDT,  # Yfii.finance
    A_BZRX: A_USDT,  # bZx Protocol
    strethaddress_to_identifier('0x2ba592F78dB6436527729929AAf6c908497cB200'): A_USDT,  # Cream finance  # noqa: E501
    strethaddress_to_identifier('0x94d863173EE77439E4292284fF13fAD54b3BA182'): A_USDT,  # Akropolis delphi  # noqa: E501
    strethaddress_to_identifier('0xfffffffFf15AbF397dA76f1dcc1A1604F45126DB'): A_USDT,  # FalconSwap Token  # noqa: E501
    strethaddress_to_identifier('0x28cb7e841ee97947a86B06fA4090C8451f64c0be'): A_USDT,  # YFLink
    strethaddress_to_identifier('0x073aF3f70516380654Ba7C5812c4Ab0255F081Bc'): A_USDT,  # TRUMPWIN
    strethaddress_to_identifier('0x70878b693A57a733A79560e33cF6a828E685d19a'): A_USDT,  # TRUMPLOSE
    strethaddress_to_identifier('0x0000000000004946c0e9F43F4Dee607b0eF1fA1c'): A_USDT,  # Chi Gas Token  # noqa: E501
    strethaddress_to_identifier('0x4639cd8cd52EC1CF2E496a606ce28D8AfB1C792F'): A_USDT,  # CBDAO
    strethaddress_to_identifier('0x3F382DbD960E3a9bbCeaE22651E88158d2791550'): A_USDT,  # AaveGotchi GHST  # noqa: E501
    strethaddress_to_identifier('0xDe201dAec04ba73166d9917Fdf08e1728E270F06'): A_USDT,  # Moji Experience Points  # noqa: E501
    strethaddress_to_identifier('0x83e6f1E41cdd28eAcEB20Cb649155049Fac3D5Aa'): A_USDT,  # Polkastarter  # noqa: E501
    strethaddress_to_identifier('0xFca59Cd816aB1eaD66534D82bc21E7515cE441CF'): A_USDT,  # Rarible
    strethaddress_to_identifier('0x49E833337ECe7aFE375e44F4E3e8481029218E5c'): A_USDT,  # Value Liquidity  # noqa: E501
    strethaddress_to_identifier('0x68A118Ef45063051Eac49c7e647CE5Ace48a68a5'): A_WETH,  # Based Money  # noqa: E501
    A_DPI: A_WETH,  # Defipulse index
    strethaddress_to_identifier('0x8A9C67fee641579dEbA04928c4BC45F66e26343A'): A_USDT,  # Jarvis reward token  # noqa: E501
    strethaddress_to_identifier('0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5'): A_USDT,  # Pickle token  # noqa: E501
    strethaddress_to_identifier('0x5bEaBAEBB3146685Dd74176f68a0721F91297D37'): A_USDT,  # Bounce token  # noqa: E501
    strethaddress_to_identifier('0xdDF7Fd345D54ff4B40079579d4C4670415DbfD0A'): A_USDT,  # Social good  # noqa: E501
    strethaddress_to_identifier('0x09a3EcAFa817268f77BE1283176B946C4ff2E608'): A_USDC,  # Mirror protocol  # noqa: E501
    strethaddress_to_identifier('0x1966d718A565566e8E202792658D7b5Ff4ECe469'): A_WETH,  # nDex
}
CRYPTOCOMPARE_SPECIAL_CASES = CRYPTOCOMPARE_SPECIAL_CASES_MAPPING.keys()
CRYPTOCOMPARE_HOURQUERYLIMIT = 2000


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


class Cryptocompare(ExternalServiceWithApiKey):
    def __init__(self, data_directory: Path, database: Optional['DBHandler']) -> None:
        super().__init__(database=database, service_name=ExternalService.CRYPTOCOMPARE)
        self.data_directory = data_directory
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        self.last_histohour_query_ts = 0
        self.last_rate_limit = 0

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
        data_range = GlobalDBHandler().get_historical_price_range(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        )
        got_cached_data = data_range is not None and data_range[0] <= timestamp <= data_range[1]
        rate_limited = self.rate_limited_in_last(seconds)
        can_query = got_cached_data or not rate_limited
        logger.debug(
            f'{"Will" if can_query else "Will not"} query '
            f'Cryptocompare history for {from_asset.identifier} -> '
            f'{to_asset.identifier} @ {timestamp}. Cached data: {got_cached_data}'
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
                response = self.session.get(querystr, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Cryptocompare API request failed due to {str(e)}') from e

            try:
                json_ret = jsonloads_dict(response.text)
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
        intermediate_asset = CRYPTOCOMPARE_SPECIAL_CASES_MAPPING[from_asset.identifier]
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
            from_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES or
            to_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES
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
            from_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES or
            to_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES
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
            from_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES or
            to_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES
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
        data_range = GlobalDBHandler().get_historical_price_range(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        )
        if data_range and now - data_range[1] < 3600 and not purge_old:
            log.debug(
                'Did not create new cache since we got cache until 1 hour ago',
                from_asset=from_asset,
                to_asset=to_asset,
            )
            return

        if purge_old:
            GlobalDBHandler().delete_historical_prices(
                from_asset=from_asset,
                to_asset=to_asset,
                source=HistoricalPriceOracle.CRYPTOCOMPARE,
            )
        self.query_and_store_historical_data(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=now,
        )

    def query_and_store_historical_data(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
    ) -> None:
        """
        Get historical hour price data from cryptocompare and populate the global DB

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        - May raise UnsupportedAsset if from/to asset is not supported by cryptocompare
        """
        log.debug(
            'Retrieving historical hour price data from cryptocompare',
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )

        now_ts = ts_now()
        # save time at start of the query, in case the query does not complete due to rate limit
        self.last_histohour_query_ts = now_ts
        range_result = GlobalDBHandler().get_historical_price_range(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        )

        if range_result is not None:
            first_cached_ts, last_cached_ts = range_result
            if timestamp > last_cached_ts:
                # We have a cache but the requested timestamp does not hit it
                new_data = self._get_histohour_data_for_range(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    from_timestamp=now_ts,
                    to_timestamp=last_cached_ts,
                )
            else:
                # only other possibility, timestamp < cached start_time
                new_data = self._get_histohour_data_for_range(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    from_timestamp=first_cached_ts,
                    to_timestamp=Timestamp(0),
                )

        else:
            new_data = self._get_histohour_data_for_range(
                from_asset=from_asset,
                to_asset=to_asset,
                from_timestamp=now_ts,
                to_timestamp=Timestamp(0),
            )

        calculated_history = list(new_data)

        if len(calculated_history) == 0:
            return

        # Let's always check for data sanity for the hourly prices.
        _check_hourly_data_sanity(calculated_history, from_asset, to_asset)
        # Turn them into the format we will enter in the DB
        prices = []
        for entry in calculated_history:
            try:
                price = Price((deserialize_price(entry['high']) + deserialize_price(entry['low'])) / 2)  # noqa: E501
                if price == Price(ZERO):
                    continue  # don't write zero prices
                prices.append(HistoricalPrice(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    source=HistoricalPriceOracle.CRYPTOCOMPARE,
                    timestamp=Timestamp(entry['time']),
                    price=price,
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.error(
                    f'{msg}. Error getting price entry from cryptocompare histohour '
                    f'price results. Skipping entry.',
                )
                continue

        GlobalDBHandler().add_historical_prices(prices)
        self.last_histohour_query_ts = ts_now()  # also save when last query finished

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
        # TODO: Figure out a better way to log and return. Only thing I can imagine
        # is nested ifs (ugly af) or a different function (meh + performance).

        # NB: check if the from..to asset price (or viceversa) is a special
        # histohour API case.
        price = self._check_and_get_special_histohour_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
        )
        if price != Price(ZERO):
            log.debug('Got historical price from cryptocompare', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp, price=price)  # noqa: E501
            return price

        # check DB cache
        price_cache_entry = GlobalDBHandler().get_historical_price(
            from_asset=from_asset,
            to_asset=to_asset,
            timestamp=timestamp,
            max_seconds_distance=3600,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        )
        if price_cache_entry and price_cache_entry.price != Price(ZERO):
            log.debug('Got historical price from cryptocompare', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp, price=price)  # noqa: E501
            return price_cache_entry.price

        # else
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

        log.debug('Got historical price from cryptocompare', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp, price=price)  # noqa: E501
        return price

    def all_coins(self) -> Dict[str, Any]:
        """
        Gets the mapping of all the cryptocompare coins

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
                    data = jsonloads_dict(f.read())
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
