import logging
from collections import deque
from enum import StrEnum
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, Optional, overload

import gevent
import requests

from rotkehlchen.assets.asset import Asset, AssetWithOracles
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
    A_USDC,
    A_USDT,
    A_WBTC,
    A_WETH,
    A_YFII,
    A_ZRX,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import HOUR_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset, WrongAssetType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKeyOptionalDB
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.interfaces import HistoricalPriceOracleWithCoinListInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ExternalService, Price, Timestamp
from rotkehlchen.utils.misc import pairwise, set_user_agent, ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import PenalizablePriceOracleMixin
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


STARKNET_TOKEN_IDENTIFIER: Final = 'STRK'
CRYPTOCOMPARE_STARKNET_HISTORICAL_PRICE_CHANGE_TS: Final = Timestamp(1715212800)
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
MAX_FSYMS_CHARS: Final = 300  # Max number of characters supported for the pricemulti endpoint fsyms argument  # noqa: E501


class CCApiUrl(StrEnum):
    PRICE = 'https://min-api.cryptocompare.com/data/price'
    MULTI_PRICE = 'https://min-api.cryptocompare.com/data/pricemulti'
    COIN_LIST = 'https://min-api.cryptocompare.com/data/all/coinlist'
    HISTORICAL_DAYS = 'https://data-api.cryptocompare.com/index/cc/v1/historical/days'
    HISTORICAL_HOURS = 'https://data-api.cryptocompare.com/index/cc/v1/historical/hours'


def _multiply_str_nums(a: str, b: str) -> str:
    """Multiplies two string numbers and returns the result as a string"""
    return str(FVal(a) * FVal(b))


def _check_hourly_data_sanity(
        data: list[dict[str, Any]],
        from_asset: AssetWithOracles,
        to_asset: AssetWithOracles,
) -> None:
    """Check that the hourly data is an array of objects having timestamps
    increasing by 1 hour.

    If not then a RemoteError is raised
    """
    index = 0
    for n1, n2 in pairwise(data):
        diff = n2['TIMESTAMP'] - n1['TIMESTAMP']
        if diff != 3600:
            raise RemoteError(
                'Unexpected data format in cryptocompare query_endpoint_histohour. '
                f'Problem at indices {index} and {index + 1} of '
                f'{from_asset.symbol}_to_{to_asset.symbol} prices. Time difference is: {diff}',
            )

        index += 2


class Cryptocompare(
        ExternalServiceWithApiKeyOptionalDB,
        HistoricalPriceOracleWithCoinListInterface,
        PenalizablePriceOracleMixin,
):
    def __init__(self, database: Optional['DBHandler']) -> None:
        HistoricalPriceOracleWithCoinListInterface.__init__(self, oracle_name='cryptocompare')
        ExternalServiceWithApiKeyOptionalDB.__init__(
            self,
            database=database,
            service_name=ExternalService.CRYPTOCOMPARE,
        )
        PenalizablePriceOracleMixin.__init__(self)
        self.session = create_session()
        set_user_agent(self.session)
        self.last_histohour_query_ts = 0
        self.db: DBHandler | None  # type: ignore  # "solve" the self.db discrepancy

    def can_query_history(
            self,
            from_asset: Asset,
            to_asset: Asset,
            timestamp: Timestamp,
            seconds: int | None = CRYPTOCOMPARE_RATE_LIMIT_WAIT_TIME,
    ) -> bool:
        """Checks if it's okay to query cryptocompare historical price. This is determined by:

        - Existence of a cached price
        - Last rate limit
        """
        data_range = GlobalDBHandler.get_historical_price_range(
            from_asset=from_asset,
            to_asset=to_asset,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        )
        got_cached_data = data_range is not None and data_range[0] <= timestamp <= data_range[1]
        if self.is_penalized() is True and got_cached_data is False:
            return False

        rate_limited = self.rate_limited_in_last(seconds)
        can_query = got_cached_data or not rate_limited
        log.debug(
            f'{"Will" if can_query else "Will not"} query '
            f'Cryptocompare history for {from_asset.identifier} -> '
            f'{to_asset.identifier} @ {timestamp}. Cached data: {got_cached_data}'
            f' rate_limited in last {seconds} seconds: {rate_limited}',
        )
        return can_query

    @overload
    def _api_query(
            self,
            url: Literal[CCApiUrl.HISTORICAL_DAYS, CCApiUrl.HISTORICAL_HOURS],
            params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """This uses Cryptocompare's Data API service.
        Currently used for handling historical prices after the STARK->STRK ticker change.
        """

    @overload
    def _api_query(
            self,
            url: Literal[CCApiUrl.PRICE, CCApiUrl.MULTI_PRICE, CCApiUrl.COIN_LIST],
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    def _api_query(
            self,
            url: CCApiUrl,
            params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Queries cryptocompare

        - May raise RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        params = params if params is not None else {}
        if api_key := self._get_api_key():
            params |= {'api_key': api_key}

        tries = CRYPTOCOMPARE_QUERY_RETRY_TIMES
        timeout = CachedSettings().get_timeout_tuple()
        while tries >= 0:
            log.debug('Querying cryptocompare', url=url, params=params)
            try:
                response = self.session.get(url, timeout=timeout, params=params)
            except requests.exceptions.RequestException as e:
                self.penalty_info.note_failure_or_penalize()
                raise RemoteError(f'Cryptocompare API request failed due to {e!s}') from e

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
                    error_message = f'Failed to query cryptocompare for: "{url}"'
                    if 'Message' in json_ret:
                        error_message += f'. Error: {json_ret["Message"]}'

                    log.warning(
                        'Cryptocompare query failure',
                        url=url,
                        error=error_message,
                        status_code=response.status_code,
                    )
                    raise RemoteError(error_message)

                return json_ret.get('Data', json_ret)
            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of Cryptocompare json_response. '
                    f'Missing key entry for {e!s}',
                ) from e

        raise AssertionError('We should never get here')

    @overload
    def _special_case_handling(
            self,
            method_name: Literal['query_endpoint_histohour'],
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            **kwargs: Any,
    ) -> list[dict[str, Any]]: ...

    @overload
    def _special_case_handling(
            self,
            method_name: Literal['query_current_price', 'query_endpoint_pricehistorical'],
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            **kwargs: Any,
    ) -> Price:
        ...

    def _special_case_handling(
            self,
            method_name: Literal[
                'query_endpoint_histohour',
                'query_current_price',
                'query_endpoint_pricehistorical',
            ],
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            **kwargs: Any,
    ) -> Price | list[dict[str, str]]:
        """Special case handling for queries that need combination of multiple asset queries

        This is hopefully temporary and can be taken care of by cryptocompare itself in the future.

        For some assets cryptocompare can only figure out the price via intermediaries.
        This function takes care of these special cases."""
        match method_name:
            case 'query_endpoint_histohour':
                method: Callable = self.query_endpoint_histohour
            case 'query_current_price':
                method = self.query_current_price
            case 'query_endpoint_pricehistorical':
                method = self.query_endpoint_pricehistorical

        intermediate_asset = CRYPTOCOMPARE_SPECIAL_CASES_MAPPING[from_asset.identifier]
        try:
            intermediate_asset = intermediate_asset.resolve_to_asset_with_oracles()
        except (UnknownAsset, WrongAssetType) as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

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
        if method_name == 'query_endpoint_histohour':
            data = []
            for idx, entry in enumerate(result1):
                entry2 = result2[idx]
                data.append({
                    'TIMESTAMP': entry['TIMESTAMP'],
                    'HIGH': _multiply_str_nums(entry['HIGH'], entry2['HIGH']),
                    'LOW': _multiply_str_nums(entry['LOW'], entry2['LOW']),
                    'OPEN': _multiply_str_nums(entry['OPEN'], entry2['OPEN']),
                    'CLOSE': _multiply_str_nums(entry['CLOSE'], entry2['CLOSE']),
                })
            return data

        return Price(result1 * result2)  # pyright: ignore  # pyright does not see the if above

    def query_endpoint_histohour(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            limit: int,
            to_timestamp: Timestamp,
            handling_special_case: bool = False,
    ) -> list[dict[str, Any]]:
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
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        params = {
            'limit': limit,
            'market': 'cadli',
            'to_ts': to_timestamp,
            'instrument': f'{cc_from_asset_symbol}-{cc_to_asset_symbol}',
        }  # As of May 9, 2024, Cryptocompare switched the Starknet token from STARK to STRK ticker
        # with STRK previously being used for the Strike token. This handles that change.
        if (
            cc_from_asset_symbol == STARKNET_TOKEN_IDENTIFIER and
            to_timestamp < CRYPTOCOMPARE_STARKNET_HISTORICAL_PRICE_CHANGE_TS
        ):
            params['instrument'] = f'STARK-{cc_to_asset_symbol}'

        return self._api_query(url=CCApiUrl.HISTORICAL_HOURS, params=params)

    def query_current_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            handling_special_case: bool = False,
    ) -> Price:
        """Wrapper for query_multiple_current_price when only querying a single price.
        Returns the asset price or ZERO_PRICE if no price is found.
        """
        return self.query_multiple_current_prices(
            from_assets=[from_asset],
            to_asset=to_asset,
            handling_special_case=handling_special_case,
        ).get(from_asset, ZERO_PRICE)

    def query_multiple_current_prices(
            self,
            from_assets: 'list[AssetWithOracles]',
            to_asset: AssetWithOracles,
            handling_special_case: bool = False,
    ) -> dict[AssetWithOracles, Price]:
        """Query the current prices of from_assets to to_asset from cryptocompare.

        Returns a dict mapping assets to prices found. Assets for which a price was not found
        are not included in the dict.

        May raise:
        - RemoteError if there is a problem reaching the cryptocompare server
            or with reading the response returned by the server
        - PriceQueryUnsupportedAsset if to_asset is not known to cryptocompare
        """
        found_prices, unpriced_assets = {}, from_assets
        # Handle cryptocompare special cases
        if not handling_special_case:
            special_assets = from_assets if to_asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES else [  # noqa: E501
                asset for asset in from_assets if asset.identifier in CRYPTOCOMPARE_SPECIAL_CASES
            ]
            for from_asset in special_assets:
                try:
                    if (price := self._special_case_handling(
                        method_name='query_current_price',
                        from_asset=from_asset,
                        to_asset=to_asset,
                    )) != ZERO_PRICE:
                        found_prices[from_asset] = price
                except (RemoteError, PriceQueryUnsupportedAsset) as e:
                    # Skip special case assets that fail but continue processing others
                    log.debug(f'CryptoCompare special case handling failed for {from_asset}: {e}')
                    continue

            if len(unpriced_assets := [asset for asset in from_assets if asset not in special_assets]) == 0:  # noqa: E501
                return found_prices

        # Convert assets to cryptocompare symbols and split the from_asset symbols into chunks
        try:
            cc_to_asset_symbol = to_asset.to_cryptocompare()
        except UnsupportedAsset as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        symbols_to_assets, fsyms_chunks, current_chunk = {}, [], ''
        for from_asset in unpriced_assets:
            try:
                symbols_to_assets[cc_symbol := from_asset.to_cryptocompare()] = from_asset
            except UnsupportedAsset as e:
                log.warning(f'Failed to find cryptocompare {to_asset!s} price for {from_asset!s} due to {e}')  # noqa: E501
                continue

            # Begin next chunk if adding cc_symbol to the current chunk will make it longer than MAX_FSYMS_CHARS  # noqa: E501
            if len(current_chunk) + len(cc_symbol) > MAX_FSYMS_CHARS:
                fsyms_chunks.append(current_chunk.rstrip(','))
                current_chunk = ''
                continue

            current_chunk += f'{cc_symbol},'  # else, add to the existing chunk

        if len(current_chunk) != 0:
            fsyms_chunks.append(current_chunk.rstrip(','))

        for fsyms in fsyms_chunks:
            try:
                if ',' in fsyms:
                    result = self._api_query(
                        url=CCApiUrl.MULTI_PRICE,
                        params={'fsyms': fsyms, 'tsyms': cc_to_asset_symbol},
                    )
                    for cc_from_symbol, price_result in result.items():
                        if cc_to_asset_symbol in price_result:
                            found_prices[symbols_to_assets[cc_from_symbol]] = Price(FVal(price_result[cc_to_asset_symbol]))  # noqa: E501
                else:
                    result = self._api_query(
                        url=CCApiUrl.PRICE,
                        params={'fsym': fsyms, 'tsyms': cc_to_asset_symbol},
                    )
                    found_prices[symbols_to_assets[fsyms]] = Price(FVal(result[cc_to_asset_symbol]))  # noqa: E501
            except (RemoteError, ValueError, KeyError) as e:
                # Skip chunks that fail but continue processing other chunks
                log.debug(f'CryptoCompare failed to query price chunk {fsyms}: {e}')
                continue

        return found_prices

    def query_endpoint_pricehistorical(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
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
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        params = {
            'limit': 1,  # number of data points to return, with 1 returning only the closest to to_ts  # noqa: E501
            'market': 'cadli',  # 24h volume-weighted average index with outlier adjustment
            'to_ts': timestamp,
            'instrument': f'{cc_from_asset_symbol}-{cc_to_asset_symbol}',
        }

        # As of May 9, 2024, Cryptocompare switched the Starknet token from STARK to STRK ticker,
        # with STRK previously being used for the Strike token. This handles that change.
        if (
            cc_from_asset_symbol == STARKNET_TOKEN_IDENTIFIER and
            timestamp < CRYPTOCOMPARE_STARKNET_HISTORICAL_PRICE_CHANGE_TS
        ):
            params['instrument'] = f'STARK-{cc_to_asset_symbol}'

        if len(result := self._api_query(url=CCApiUrl.HISTORICAL_DAYS, params=params)) == 0:
            return ZERO_PRICE

        try:
            return deserialize_price(result[0]['CLOSE'])
        except (DeserializationError, KeyError) as e:
            log.error(f'Failed to retrieve price from Cryptocompare API. Got result: {result}')
            raise RemoteError(
                f'Failed to deserialize {cc_from_asset_symbol}-{cc_to_asset_symbol} '
                f'historical price data from Cryptocompare',
            ) from e

    def _get_histohour_data_for_range(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> deque[dict[str, Any]]:
        """Query histohour data from cryptocompare for a time range going backwards in time

        Will stop when to_timestamp is reached OR when no more prices are returned

        Returns a list of histohour entries with increasing timestamp. Starting from
        to_timestamp (or higher) if no data and ending in from_timestamp or lower, if no data

        May raise:
        - RemoteError if there is problems with the query
        """
        msg = '_get_histohour_data_for_range from_timestamp should be bigger than to_timestamp'
        assert from_timestamp >= to_timestamp, msg

        calculated_history: deque[dict[str, Any]] = deque()
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
                limit=CRYPTOCOMPARE_HOURQUERYLIMIT,
                to_timestamp=end_date,
            )
            if all(FVal(x['CLOSE']) == ZERO for x in resp):
                # all prices zero Means we have reached the end of available prices
                break

            end_date = Timestamp(resp[0]['TIMESTAMP'] - HOUR_IN_SECONDS)
            if len(calculated_history) != 0:
                # Check for overlap and merge
                if calculated_history[0]['TIMESTAMP'] == resp[-1]['TIMESTAMP']:
                    resp = resp[:-1]
                calculated_history.extendleft(reversed(resp))
            else:
                calculated_history = deque(resp)

            if end_date - to_timestamp <= HOUR_IN_SECONDS:
                while (
                    len(calculated_history) != 0 and
                    calculated_history[0]['TIMESTAMP'] <= to_timestamp
                ):
                    calculated_history.popleft()
                break

        return calculated_history

    def create_cache(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
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
        data_range = GlobalDBHandler.get_historical_price_range(
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
            GlobalDBHandler.delete_historical_prices(
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
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
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
        range_result = GlobalDBHandler.get_historical_price_range(
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
        # Turn them into the format we will enter into the DB
        prices = []
        for entry in calculated_history:
            try:
                price = Price((deserialize_price(entry['HIGH']) + deserialize_price(entry['LOW'])) / 2)  # noqa: E501
                if price == ZERO_PRICE:
                    continue  # don't write zero prices
                prices.append(HistoricalPrice(
                    from_asset=from_asset,
                    to_asset=to_asset,
                    source=HistoricalPriceOracle.CRYPTOCOMPARE,
                    timestamp=Timestamp(entry['TIMESTAMP']),
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

        GlobalDBHandler.add_historical_prices(prices)
        self.last_histohour_query_ts = ts_now()  # also save when last query finished

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
        1. Query the historical price endpoint
        2. Return the price if found
        3. Fail if no price exists

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is known to miss from cryptocompare
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from cryptocompare
        - RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        try:
            from_asset = from_asset.resolve_to_asset_with_oracles()
            to_asset = to_asset.resolve_to_asset_with_oracles()
        except (UnknownAsset, WrongAssetType) as e:
            raise PriceQueryUnsupportedAsset(e.identifier) from e

        price = self.query_endpoint_pricehistorical(from_asset, to_asset, timestamp)
        if price == ZERO_PRICE:
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )

        log.debug('Got historical price from cryptocompare', from_asset=from_asset, to_asset=to_asset, timestamp=timestamp, price=price)  # noqa: E501
        return price

    def all_coins(self) -> dict[str, dict[str, Any]]:
        """
        Gets the mapping of all the cryptocompare coins.

        May raise:
        - RemoteError if there is a problem reaching the cryptocompare server
        or with reading the response returned by the server
        """
        if (data := self.maybe_get_cached_coinlist(considered_recent_secs=WEEK_IN_SECONDS)) is None:  # noqa: E501
            self.cache_coinlist(data := self._api_query(CCApiUrl.COIN_LIST))

        return data
