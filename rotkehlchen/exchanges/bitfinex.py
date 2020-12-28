import hashlib
import hmac
import logging
import re
from collections import defaultdict
from datetime import datetime
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
    overload,
)
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore
from requests.adapters import Response
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import BITFINEX_TO_WORLD, asset_from_bitfinex
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    SystemClockNotSyncedError,
    UnknownAsset,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Error codes that we handle nicely
API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE = 10114  # small nonce (from timestamp in ms)
API_KEY_ERROR_CODE = 10100
API_KEY_ERROR_MESSAGE = (
    'Provided API key/secret is invalid or does not have enough permissions. '
    'Make sure it has get/read permission of both "Balances" and "Account History" enabled.'
)
# Rate Limits and retry
API_RATE_LIMITS_ERROR_MESSAGE = 'ERR_RATE_LIMIT'
API_REQUEST_RETRY_TIMES = 2
API_REQUEST_RETRY_AFTER_SECONDS = 60
# Max limits for all API v2 endpoints
API_TRADES_MAX_LIMIT = 2500
API_MOVEMENTS_MAX_LIMIT = 1000
# Sorting mode
API_TRADES_SORTING_MODE = 1  # ascending
API_MOVEMENTS_SORTING_MODE = 1  # ascending, TBC
# Minimum response item length per endpoint
API_WALLET_MIN_RESULT_LENGTH = 3
API_TRADES_MIN_RESULT_LENGTH = 11
API_MOVEMENTS_MIN_RESULT_LENGTH = 22

DeserializationMethod = Callable[..., Union[Trade, AssetMovement]]  # ... due to keyword args


class CurrenciesResponse(NamedTuple):
    success: bool
    response: Response
    currencies: List[str]


class CurrencyMapResponse(NamedTuple):
    success: bool
    response: Response
    currency_map: Dict[str, str]


class ExchangePairsResponse(NamedTuple):
    success: bool
    response: Response
    pairs: List[str]


class ErrorResponseData(NamedTuple):
    error_code: Optional[int] = None
    reason: Optional[str] = None


class Bitfinex(ExchangeInterface):
    """Bitfinex exchange api docs:
    https://docs.bitfinex.com/docs
    """
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(str(Location.BITFINEX), api_key, secret, database)
        self.base_uri = 'https://api.bitfinex.com'
        self.msg_aggregator = msg_aggregator
        self.nonce_lock = Semaphore()

    def _api_query(
            self,
            endpoint: Literal[
                'configs_list_currency',
                'configs_list_pair_exchange',
                'configs_map_currency_symbol',
                'movements',
                'trades',
                'wallets',
            ],
            options: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Request a Bitfinex API v2 endpoint (from `endpoint`).
        """
        call_options = options.copy() if options else {}
        for header in ('Content-Type', 'bfx-apikey', 'bfx-nonce', 'bfx-signature'):
            self.session.headers.pop(header, None)

        if endpoint == 'configs_list_currency':
            method = 'get'
            api_path = 'v2/conf/pub:list:currency'
            request_url = f'{self.base_uri}/{api_path}'
        elif endpoint == 'configs_list_pair_exchange':
            method = 'get'
            api_path = 'v2/conf/pub:list:pair:exchange'
            request_url = f'{self.base_uri}/{api_path}'
        elif endpoint == 'configs_map_currency_symbol':
            method = 'get'
            api_path = 'v2/conf/pub:map:currency:sym'
            request_url = f'{self.base_uri}/{api_path}'
        elif endpoint == 'movements':
            method = 'post'
            api_path = 'v2/auth/r/movements/hist'
            request_url = f'{self.base_uri}/{api_path}?{urlencode(call_options)}'
        elif endpoint == 'trades':
            method = 'post'
            api_path = 'v2/auth/r/trades/hist'
            request_url = f'{self.base_uri}/{api_path}?{urlencode(call_options)}'
        elif endpoint == 'wallets':
            method = 'post'
            api_path = 'v2/auth/r/wallets'
            request_url = f'{self.base_uri}/{api_path}'
        else:
            raise AssertionError(f'Unexpected {self.name} endpoint type: {endpoint}')

        with self.nonce_lock:
            # Protect this region with a lock since Bitfinex will reject
            # non-increasing nonces for authenticated endpoints
            if endpoint in {'movements', 'trades', 'wallets'}:
                nonce = str(ts_now_in_ms())
                message = f'/api/{api_path}{nonce}'
                signature = hmac.new(
                    self.secret,
                    msg=message.encode('utf-8'),
                    digestmod=hashlib.sha384,
                ).hexdigest()
                self.session.headers.update({
                    'Content-Type': 'application/json',
                    'bfx-apikey': self.api_key,
                    'bfx-nonce': nonce,
                    'bfx-signature': signature,
                })

            log.debug(f'{self.name} API request', request_url=request_url)
            try:
                response = self.session.request(
                    method=method,
                    url=request_url,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} {method} request at {request_url} connection error: {str(e)}.',
                ) from e

        return response

    @overload  # noqa: F811
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal['trades'],
            currency_map: Dict[str, str],
    ) -> List[Trade]:
        ...

    @overload  # noqa: F811
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal['asset_movements'],
            currency_map: Dict[str, str],
    ) -> List[AssetMovement]:
        ...

    def _api_query_paginated(
            self,
            options: Dict[str, Any],
            case: Literal['trades', 'asset_movements'],
            currency_map: Dict[str, str],
    ) -> Union[List[Trade], List[AssetMovement]]:
        """Request a Bitfinex API v2 endpoint paginating via an options
        attribute.

        Pagination attribute criteria per endpoint:
          - trades: from `start_ts` to `end_ts` (as offset) with limit 2500.
          - movements: from `start_ts` to `end_ts` (as offset) with limit 1000.

        Error codes documentation:
        https://docs.bitfinex.com/docs/abbreviations-glossary#errorinfo-codes

        Rates limit documentation:
        https://docs.bitfinex.com/docs/requirements-and-limitations#rest-rate-limits
        """
        deserialization_method: DeserializationMethod
        endpoint: Literal['trades', 'movements']
        response_case: Literal['trades', 'asset_movements']
        if case == 'trades':
            endpoint = 'trades'
            response_case = 'trades'
            deserialization_method = self._deserialize_trade
            expected_raw_result_length = API_TRADES_MIN_RESULT_LENGTH
            id_index = 0
            timestamp_index = 2
        elif case == 'asset_movements':
            endpoint = 'movements'
            response_case = 'asset_movements'
            deserialization_method = self._deserialize_asset_movement
            expected_raw_result_length = API_MOVEMENTS_MIN_RESULT_LENGTH
            id_index = 0
            timestamp_index = 5
        else:
            raise AssertionError(f'Unexpected {self.name} case: {case}')

        call_options = options.copy()
        limit = options['limit']
        results: Union[List[Trade], List[AssetMovement]] = []  # type: ignore # bug list nothing
        last_result_id = None
        last_result_timestamp = None
        retries_left = API_REQUEST_RETRY_TIMES
        while retries_left >= 0:
            response = self._api_query(
                endpoint=endpoint,
                options=call_options,
            )
            if response.status_code != HTTPStatus.OK:
                # NB: check if the rate limits have been hit (response JSON as dict)
                try:
                    response_dict = rlk_jsonloads_dict(response.text)
                except (AssertionError, JSONDecodeError):
                    msg = (
                        f'Error decoding {self.name} {case} unsuccessful response JSON as dict. '
                        f'Continue decoding unsuccessful response as a JSON list.'
                    )
                    log.debug(msg, options=call_options)
                else:
                    if response_dict.get('error', None) == API_RATE_LIMITS_ERROR_MESSAGE:
                        if retries_left == 0:
                            raise RemoteError(
                                f'{self.name} {case} request failed after retrying '
                                f'{API_REQUEST_RETRY_TIMES} times.',
                            )
                        # Trigger retry
                        log.debug(
                            f'{self.name} {case} request reached the rate limits. Backing off',
                            seconds=API_REQUEST_RETRY_AFTER_SECONDS,
                            options=call_options,
                        )
                        retries_left -= 1
                        gevent.sleep(API_REQUEST_RETRY_AFTER_SECONDS)
                        continue
                    # As this should not happend, better to log it
                    log.error(
                        f'Unexpected {self.name} {case} unsuccessful response JSON. '
                        f'Continue decoding unsuccessful response a JSON list.',
                        options=call_options,
                    )

                return self._process_unsuccessful_response(
                    response=response,
                    case=response_case,
                )
            try:
                response_list = rlk_jsonloads_list(response.text)
            except JSONDecodeError:
                msg = f'{self.name} {case} returned invalid JSON response: {response.text}.'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Got remote error while querying {self.name} {case}: {msg}',
                )
                return []  # type: ignore # bug list nothing

            for raw_result in response_list:
                if len(raw_result) < expected_raw_result_length:
                    log.error(
                        f'Error processing a {self.name} {case} result. '
                        f'Found less items than expected',
                        raw_result=raw_result,
                    )
                    self.msg_aggregator.add_error(
                        f'Failed to deserialize a {self.name} {case} result. '
                        f'Check logs for details. Ignoring it.',
                    )
                    continue

                if raw_result[timestamp_index] > options['end']:
                    log.debug(
                        f'Unexpected result requesting {self.name} {case}. '
                        f'Result timestamp {raw_result[timestamp_index]} is greater than '
                        f'end filter {options["end"]}. Stop requesting.',
                        raw_result=raw_result,
                    )
                    break

                if (
                    results and
                    raw_result[id_index] <= last_result_id and
                    raw_result[timestamp_index] <= last_result_timestamp
                ):
                    log.debug(
                        f'Skipped {self.name} {case} result. Already processed',
                        raw_result=raw_result,
                    )
                    continue

                # Only asset movements: skip if raw_result status is not 'COMPLETED'
                if case == 'asset_movements' and raw_result[9] != 'COMPLETED':
                    log.debug(
                        f'Skipped {self.name} {case} result. Status is not completed',
                        raw_result=raw_result,
                    )
                    continue

                try:
                    result = deserialization_method(
                        raw_result=raw_result,
                        currency_map=currency_map,
                    )
                except DeserializationError as e:
                    msg = str(e)
                    log.error(
                        f'Error processing a {self.name} {case} result.',
                        raw_result=raw_result,
                        error=msg,
                    )
                    self.msg_aggregator.add_error(
                        f'Failed to deserialize a {self.name} {case} result. '
                        f'Check logs for details. Ignoring it.',
                    )
                    continue
                else:
                    results.append(result)  # type: ignore # type is known
                    last_result_id = raw_result[id_index]
                    last_result_timestamp = raw_result[timestamp_index]

            if len(response_list) < limit:
                break

            # Update pagination params per endpoint
            # NB: re-assign dict instead of update, prevent lose call args values
            call_options = call_options.copy()
            call_options.update({
                'start': results[-1].timestamp * 1000,
            })

        return results

    def _check_for_system_clock_not_synced_error(
            self,
            error_code: Optional[int] = None,
    ) -> None:
        if error_code == API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE:
            raise SystemClockNotSyncedError(
                current_time=str(datetime.now()),
                remote_server=f'{self.name}',
            )

    @staticmethod
    def _deserialize_asset_movement(
            raw_result: List[Any],
            currency_map: Dict[str, str],
    ) -> AssetMovement:
        """Process an asset movement (i.e. deposit or withdrawal) from Bitfinex
        and deserialize it.

        Bitfinex support confirmed the following in regards to
        DESTINATION_ADDRESS and TRANSACTION_ID:
          - Fiat movement: both attributes won't show any value.
          - Cryptocurrency movement: address and tx id on the blockchain.

        Timestamp is from MTS_STARTED (when the movement was created), and not
        from MTS_UPDATED (when it was completed/cancelled).

        Can raise DeserializationError.

        Schema reference in:
        https://docs.bitfinex.com/reference#rest-auth-movements
        """
        if raw_result[9] != 'COMPLETED':
            raise DeserializationError(
                f'Unexpected bitfinex movement with status: {raw_result[5]}. '
                f'Only completed movements are processed. Raw movement: {raw_result}',
            )
        try:
            fee_asset = asset_from_bitfinex(
                bitfinex_name=raw_result[1],
                currency_map=currency_map,
            )
        except (UnknownAsset, UnsupportedAsset) as e:
            asset_tag = 'Unknown' if isinstance(e, UnknownAsset) else 'Unsupported'
            raise DeserializationError(
                f'{asset_tag} {e.asset_name} found while processing movement asset '
                f'due to: {str(e)}',
            ) from e

        amount = deserialize_asset_amount(raw_result[12])
        category = (
            AssetMovementCategory.DEPOSIT
            if amount > ZERO
            else AssetMovementCategory.WITHDRAWAL
        )
        address = None
        transaction_id = None
        if fee_asset.is_fiat() is False:
            address = raw_result[16]
            transaction_id = raw_result[20]

        asset_movement = AssetMovement(
            timestamp=Timestamp(int(raw_result[5] / 1000)),
            location=Location.BITFINEX,
            category=category,
            address=address,
            transaction_id=transaction_id,
            asset=fee_asset,
            amount=abs(amount),
            fee_asset=fee_asset,
            fee=Fee(abs(deserialize_fee(raw_result[13]))),
            link=str(raw_result[0]),
        )
        return asset_movement

    @staticmethod
    def _deserialize_trade(
            raw_result: List[Any],
            currency_map: Dict[str, str],
    ) -> Trade:
        """Process a trade result from Bitfinex and deserialize it.

        The base and quote assets are instantiated using the `fee_currency_symbol`
        (from raw_result[10]) over the pair (from raw_result[1]).

        Known pairs format: 'ETHUST', 'ETH:UST'.

        Can raise DeserializationError.

        Schema reference in:
        https://docs.bitfinex.com/reference#rest-auth-trades
        """
        amount = deserialize_asset_amount(raw_result[4])
        trade_type = TradeType.BUY if amount >= ZERO else TradeType.SELL
        bfx_pair = raw_result[1]
        bfx_fee_currency_symbol = raw_result[10]
        if bfx_pair.startswith(bfx_fee_currency_symbol):
            regex = re.compile(fr'^({bfx_fee_currency_symbol})\W*(\w+)$')
        elif bfx_pair.endswith(bfx_fee_currency_symbol):
            regex = re.compile(fr'^(\w+)\W*({bfx_fee_currency_symbol})$')
        else:
            raise DeserializationError(
                f'Could not deserialize bitfinex trade pair {raw_result[1]} '
                f'using fee_currency symbol {bfx_fee_currency_symbol}. '
                f'Raw trade: {raw_result}',
            )

        match = regex.match(bfx_pair)
        if match is None:
            raise DeserializationError(
                f'Unexpected error deserializing bitfinex trade pair: {raw_result[1]} '
                f'using fee_currency symbol {bfx_fee_currency_symbol}. '
                f'Trade pair does not match the pattern. Raw trade: {raw_result}',
            )

        bfx_base_asset_symbol, bfx_quote_asset_symbol = match.groups()
        try:
            base_asset = asset_from_bitfinex(
                bitfinex_name=bfx_base_asset_symbol,
                currency_map=currency_map,
            )
            quote_asset = asset_from_bitfinex(
                bitfinex_name=bfx_quote_asset_symbol,
                currency_map=currency_map,
            )
        except (UnknownAsset, UnsupportedAsset) as e:
            asset_tag = 'Unknown' if isinstance(e, UnknownAsset) else 'Unsupported'
            raise DeserializationError(
                f'{asset_tag} {e.asset_name} found while processing trade pair due to: {str(e)}',
            ) from e

        trade = Trade(
            timestamp=Timestamp(int(raw_result[2] / 1000)),
            location=Location.BITFINEX,
            pair=TradePair(f'{base_asset.identifier}_{quote_asset.identifier}'),
            trade_type=trade_type,
            amount=AssetAmount(abs(amount)),
            rate=deserialize_price(raw_result[5]),
            fee=Fee(abs(deserialize_fee(raw_result[9]))),
            fee_currency=quote_asset if trade_type == TradeType.BUY else base_asset,
            link=str(raw_result[0]),
            notes='',
        )
        return trade

    @staticmethod
    def _get_error_response_data(response_list: List[Any]) -> ErrorResponseData:
        """Given an error response, return the error code and the reason.
        """
        error_code = None
        reason = None
        if len(response_list) > 1:
            error_code = response_list[1]
        if len(response_list) > 2:
            reason = response_list[2]

        return ErrorResponseData(
            error_code=error_code,
            reason=reason,
        )

    def _query_currencies(self) -> CurrenciesResponse:
        """Query and return the list of all the currencies supported in
        `<CurrenciesResponse>.currencies`.
        Otherwise populate <CurrenciesResponse> with data that each endpoint
        can process as an unsuccessful request.
        """
        was_successful = True
        currencies = []
        response = self._api_query('configs_list_currency')

        if response.status_code != HTTPStatus.OK:
            was_successful = False
            log.error(f'{self.name} currencies list query failed. Check further logs')
        else:
            try:
                response_list = rlk_jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} currencies list returned invalid JSON response. '
                    f'Check further logs',
                )
            else:
                currencies = response_list[0]

        return CurrenciesResponse(
            success=was_successful,
            response=response,
            currencies=currencies,
        )

    def _query_currency_map(self) -> CurrencyMapResponse:
        """Query the list that maps standard currency symbols with the version
        of the Bitfinex API. If the request is successful and the list format
        as well, return it as dict in `<CurrencyMapResponse>.currency_map`.
        Otherwise populate <CurrencyMapResponse> with data that each endpoint
        can process as an unsuccessful request.

        API result format is: [[[<bitfinex_symbol>, <symbol>], ...]]

        May raise IndexError if the list is empty.
        """
        was_successful = True
        currency_map = {}
        response = self._api_query('configs_map_currency_symbol')

        if response.status_code != HTTPStatus.OK:
            was_successful = False
            log.error(f'{self.name} currency map query failed. Check further logs')
        else:
            try:
                response_list = rlk_jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} currency map returned invalid JSON response. Check further logs',
                )
            else:
                currency_map = dict(response_list[0])
                currency_map.update(BITFINEX_TO_WORLD)

        return CurrencyMapResponse(
            success=was_successful,
            response=response,
            currency_map=currency_map,
        )

    def _query_exchange_pairs(self) -> ExchangePairsResponse:
        """Query and return the list of the exchange (trades) pairs in
        `<ExchangePairsResponse>.pairs`.
        Otherwise populate <ExchangePairsResponse> with data that each endpoint
        can process as an unsuccessful request.
        """
        was_successful = True
        pairs = []
        response = self._api_query('configs_list_pair_exchange')

        if response.status_code != HTTPStatus.OK:
            was_successful = False
            log.error(f'{self.name} exchange pairs list query failed. Check further logs')
        else:
            try:
                response_list = rlk_jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} exchange pairs list returned invalid JSON response. '
                    f'Check further logs',
                )
            else:
                pairs = response_list[0]

        return ExchangePairsResponse(
            success=was_successful,
            response=response,
            pairs=pairs,
        )

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['validate_api_key'],
    ) -> Tuple[bool, str]:
        ...

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['balances'],
    ) -> Tuple[Optional[Dict[Asset, Balance]], str]:
        ...

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['trades'],
    ) -> List[Trade]:
        ...

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['asset_movements'],
    ) -> List[AssetMovement]:
        ...

    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key', 'balances', 'trades', 'asset_movements'],
    ) -> Union[
        List,
        Tuple[bool, str],
        Tuple[Optional[Dict[Asset, Balance]], str],
    ]:
        """This function processes not successful responses for the following
        cases listed in `case`.
        """
        try:
            response_list = rlk_jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON response: {response.text}.'
            log.error(msg)

            if case in {'validate_api_key', 'balances'}:
                raise RemoteError(msg) from e
            if case in {'trades', 'asset_movements'}:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying {self.name} {case}: {msg}',
                )
                return []

            raise AssertionError(f'Unexpected {self.name} response_case: {case}') from e

        error_data = self._get_error_response_data(response_list)
        self._check_for_system_clock_not_synced_error(error_data.error_code)
        # Errors related with the API key return a human readable message
        if case == 'validate_api_key' and error_data.error_code == API_KEY_ERROR_CODE:
            return False, API_KEY_ERROR_MESSAGE

        # Below any other error not related with the system clock or the API key
        reason = error_data.reason or response.text
        msg = (
            f'{self.name} query responded with error status code: {response.status_code} '
            f'and text: {reason}.'
        )
        log.error(msg)

        if case == 'validate_api_key':
            raise RemoteError(msg)
        if case == 'balances':
            return None, msg
        if case in {'trades', 'asset_movements'}:
            self.msg_aggregator.add_error(
                f'Got remote error while querying {self.name} {case}: {msg}',
            )
            return []

        raise AssertionError(f'Unexpected {self.name} response_case: {case}')

    def first_connection(self) -> None:
        self.first_connection_made = True

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict[Asset, Balance]], str]:
        """Return the account exchange balances on Bitfinex

        The wallets endpoint returns a list where each item is a currency wallet.
        Each currency wallet has type (i.e. exchange, margin, funding), currency,
        balance, etc. Currencies (tickers) are in Bitfinex format and must be
        standardized.

        Endpoint documentation:
        https://docs.bitfinex.com/reference#rest-auth-wallets
        """
        try:
            currency_map_response = self._query_currency_map()
        except IndexError:
            msg = f'Error processing {self.name} currency map. Response is empty'
            log.error(msg)
            return None, msg

        if currency_map_response.success is False:
            result, msg = self._process_unsuccessful_response(
                response=currency_map_response.response,
                case='balances',
            )
            return result, msg

        response = self._api_query('wallets')
        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='balances',
            )
            return result, msg
        try:
            response_list = rlk_jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON response: {response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        # Wallet items indexes
        currency_index = 1
        balance_index = 2
        asset_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        asset_usd_price: Dict[Asset, Price] = {}
        for wallet in response_list:
            if len(wallet) < API_WALLET_MIN_RESULT_LENGTH or wallet[balance_index] <= 0:
                continue

            try:
                asset = asset_from_bitfinex(
                    bitfinex_name=wallet[currency_index],
                    currency_map=currency_map_response.currency_map,
                )
            except (UnknownAsset, UnsupportedAsset) as e:
                asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                self.msg_aggregator.add_warning(
                    f'Found {asset_tag} {self.name} asset {e.asset_name} due to: {str(e)}. '
                    f'Ignoring its balance query.',
                )
                continue

            if asset not in asset_usd_price:
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing {self.name} balance result due to inability to '
                        f'query USD price: {str(e)}. Skipping balance result.',
                    )
                    continue

                asset_usd_price[asset] = usd_price

            amount = FVal(wallet[balance_index])
            asset_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * asset_usd_price[asset],
            )

        return dict(asset_balance), ''

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Return the account deposits and withdrawals on Bitfinex.

        Endpoint documentation:
        https://docs.bitfinex.com/reference#rest-auth-movements

        TODO: Check if 'sort' by ascending works.
        I got in touch with Bitfinex support asking about the default
        sorting mode, as per their documentation this endpoint does not accept
        a 'sort' query parameter and it is unknown in which mode the results
        come.
        They email me back confirming sorting is in descending mode and that I
        could try using the 'sort' query parameter.
        """
        try:
            currency_map_response = self._query_currency_map()
        except IndexError:
            self.msg_aggregator.add_error(
                f'Error processing {self.name} currency map. Response is empty',
            )
            return []

        if currency_map_response.success is False:
            return self._process_unsuccessful_response(
                response=currency_map_response.response,
                case='asset_movements',
            )

        options = {
            'start': start_ts * 1000,
            'end': end_ts * 1000,
            'limit': API_MOVEMENTS_MAX_LIMIT,
            'sort': API_MOVEMENTS_SORTING_MODE,
        }
        asset_movements: List[AssetMovement] = self._api_query_paginated(
            options=options,
            case='asset_movements',
            currency_map=currency_map_response.currency_map,
        )
        return asset_movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Return the account trades on Bitfinex.

        Endpoint documentation:
        https://docs.bitfinex.com/reference#rest-auth-trades
        """
        try:
            currency_map_response = self._query_currency_map()
        except IndexError:
            self.msg_aggregator.add_error(
                f'Error processing {self.name} currency map. Response is empty',
            )
            return []

        if currency_map_response.success is False:
            return self._process_unsuccessful_response(
                response=currency_map_response.response,
                case='trades',
            )

        options = {
            'start': start_ts * 1000,
            'end': end_ts * 1000,
            'limit': API_TRADES_MAX_LIMIT,
            'sort': API_TRADES_SORTING_MODE,
        }
        trades: List[Trade] = self._api_query_paginated(
            options=options,
            case='trades',
            currency_map=currency_map_response.currency_map,
        )
        return trades

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Bitfinex API key is good for usage in Rotki.

        Makes sure that the following permissions are given to the key:
        - Account History: get historical balances entries and trade information.
        - Wallets: get wallet balances and addresses.
        """
        response = self._api_query('wallets')

        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='validate_api_key',
            )
            return result, msg

        return True, ''
