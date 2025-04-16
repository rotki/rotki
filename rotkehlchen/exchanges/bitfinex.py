import hashlib
import hmac
import json
import logging
import operator
from collections import defaultdict
from collections.abc import Callable, Sequence
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, overload
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore
from requests.adapters import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import BITFINEX_EXCHANGE_TEST_ASSETS, asset_from_bitfinex
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp,
    deserialize_timestamp_ms_from_intms,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Error codes that we handle nicely
API_ERR_AUTH_NONCE_CODE = 10114  # small nonce (from timestamp in ms)
API_ERR_AUTH_NONCE_MESSAGE = (
    'Bitfinex nonce too low error. Is the local system clock in synced?'
)
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
# Minimum response item length per endpoint
API_WALLET_MIN_RESULT_LENGTH = 3
API_TRADES_MIN_RESULT_LENGTH = 11
API_MOVEMENTS_MIN_RESULT_LENGTH = 22

DeserializationMethod = Callable[..., list[SwapEvent] | list[AssetMovement]]  # ... due to keyword args  # noqa: E501


class CurrenciesResponse(NamedTuple):
    success: bool
    response: Response
    currencies: list[str]


class ExchangePairsResponse(NamedTuple):
    success: bool
    response: Response
    pairs: list[str]


class ErrorResponseData(NamedTuple):
    error_code: int | None = None
    reason: str | None = None


class Bitfinex(ExchangeInterface):
    """Bitfinex exchange api docs:
    https://docs.bitfinex.com/docs
    """
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.BITFINEX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = 'https://api.bitfinex.com'
        self.session.headers.update({'bfx-apikey': self.api_key})
        self.nonce_lock = Semaphore()

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'bfx-apikey': self.api_key})
        return changed

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
            options: dict[str, Any] | None = None,
    ) -> Response:
        """Request a Bitfinex API v2 endpoint (from `endpoint`).
        """
        call_options = options.copy() if options else {}
        for header in ('Content-Type', 'bfx-nonce', 'bfx-signature'):
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
                    f'{self.name} {method} request at {request_url} connection error: {e!s}.',
                ) from e

        return response

    def _api_query_paginated(
            self,
            options: dict[str, Any],
            case: Literal['trades', 'asset_movements'],
    ) -> tuple[list['HistoryBaseEntry'], bool]:
        """Request a Bitfinex API v2 endpoint paginating via an options
        attribute.

        Pagination attribute criteria per endpoint:
          - trades: from `start_ts` to `end_ts` (as offset) with limit 2500.
          - movements: from `start_ts` to `end_ts` (as offset) with limit 1000.

        Error codes documentation:
        https://docs.bitfinex.com/docs/abbreviations-glossary#errorinfo-codes

        Rates limit documentation:
        https://docs.bitfinex.com/docs/requirements-and-limitations#rest-rate-limits

        Returns a tuple containing the list of events found and a boolean flag
        indicating if there were errors.
        """
        endpoint: Literal['trades', 'movements']
        case_: Literal['trades', 'asset_movements']
        if case == 'trades':
            endpoint = 'trades'
            case_ = 'trades'
        elif case == 'asset_movements':
            endpoint = 'movements'
            case_ = 'asset_movements'
        else:
            raise AssertionError(f'Unexpected {self.name} case: {case}')

        call_options = options.copy()
        limit = options['limit']
        results: list[HistoryBaseEntry] = []
        processed_result_ids: set[str] = set()
        retries_left = API_REQUEST_RETRY_TIMES
        while retries_left >= 0:
            response = self._api_query(
                endpoint=endpoint,
                options=call_options,
            )
            if response.status_code != HTTPStatus.OK:
                try:
                    error_response = json.loads(response.text)
                except JSONDecodeError:
                    msg = f'{self.name} {case} returned an invalid JSON response: {response.text}.'
                    log.error(msg, options=call_options)
                    self.msg_aggregator.add_error(
                        f'Got remote error while querying {self.name} {case}: {msg}',
                    )
                    return results, True

                # Check if the rate limits have been hit (response JSON as dict)
                if isinstance(error_response, dict):
                    if error_response.get('error', None) == API_RATE_LIMITS_ERROR_MESSAGE:
                        if retries_left == 0:
                            msg = (
                                f'{self.name} {case} request failed after retrying '
                                f'{API_REQUEST_RETRY_TIMES} times.'
                            )
                            self.msg_aggregator.add_error(
                                f'Got remote error while querying {self.name} {case}: {msg}',
                            )
                            return results, True

                        # Trigger retry
                        log.debug(
                            f'{self.name} {case} request reached the rate limits. Backing off',
                            seconds=API_REQUEST_RETRY_AFTER_SECONDS,
                            options=call_options,
                        )
                        retries_left -= 1
                        gevent.sleep(API_REQUEST_RETRY_AFTER_SECONDS)
                        continue

                    # Unexpected JSON dict case, better to log it
                    msg = f'Unexpected {self.name} {case} unsuccessful response JSON'
                    log.error(msg, error_response=error_response)
                    self.msg_aggregator.add_error(
                        f'Got remote error while querying {self.name} {case}: {msg}',
                    )
                    return results, True

                return self._process_unsuccessful_response(
                    response=response,
                    case=case_,
                )

            try:
                response_list = jsonloads_list(response.text)
            except JSONDecodeError:
                msg = f'{self.name} {case} returned invalid JSON response: {response.text}.'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Got remote error while querying {self.name} {case}: {msg}',
                )
                return results, True

            results.extend(self._deserialize_api_query_paginated_results(
                case=case_,
                options=call_options,
                raw_results=response_list,
                processed_result_ids=processed_result_ids,
            ))

            if len(response_list) < limit or len(results) == 0:
                break
            # Update pagination params per endpoint
            # NB: Copying the dict before updating it prevents losing the call args values
            call_options = call_options.copy()
            last_item = results[-1]
            call_options.update({'start': last_item.timestamp})

        return results, False

    def _deserialize_api_query_paginated_results(
            self,
            case: Literal['trades', 'asset_movements'],
            options: dict[str, Any],
            raw_results: list[list[Any]],
            processed_result_ids: set[str],
    ) -> list['HistoryBaseEntry']:
        deserialization_method: DeserializationMethod
        if case == 'trades':
            deserialization_method = self._deserialize_trade
            expected_raw_result_length = API_TRADES_MIN_RESULT_LENGTH
            id_index = 0
            timestamp_index = 2
        elif case == 'asset_movements':
            deserialization_method = self._deserialize_asset_movement
            expected_raw_result_length = API_MOVEMENTS_MIN_RESULT_LENGTH
            id_index = 0
            timestamp_index = 5
        else:
            raise AssertionError(f'Unexpected {self.name} case: {case}')

        # NB: sort movements in ascending mode (via its identifier) due to
        # the lack of 'sort' query parameter.
        if case == 'asset_movements':
            raw_results.sort(key=operator.itemgetter(id_index))

        results: list[HistoryBaseEntry] = []
        for raw_result in raw_results:
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

            if (result_id := str(raw_result[id_index])) in processed_result_ids:
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
                results.extend(deserialization_method(raw_result=raw_result))
                processed_result_ids.add(result_id)
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
            except UnsupportedAsset as e:
                msg = (
                    f'Found {self.name} {case} with unsupported '
                    f'asset {e.identifier}'
                )
                log.warning(f'{msg}. raw_data={raw_result}')
                self.msg_aggregator.add_warning(f'{msg}. Ignoring {case}')
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details=case,
                )

        return results

    def _deserialize_asset_movement(self, raw_result: list[Any]) -> list[AssetMovement]:
        """Process an asset movement (i.e. deposit or withdrawal) from Bitfinex
        and deserialize it.

        Bitfinex support confirmed the following in regards to
        DESTINATION_ADDRESS and TRANSACTION_ID:
          - Fiat movement: both attributes won't show any value.
          - Cryptocurrency movement: address and tx id on the blockchain.

        Timestamp is from MTS_STARTED (when the movement was created), and not
        from MTS_UPDATED (when it was completed/cancelled).

        Can raise:
         - DeserializationError.
         - UnknownAsset
         - UnsupportedAsset

        Schema reference in:
        https://docs.bitfinex.com/reference#rest-auth-movements
        """
        if raw_result[9] != 'COMPLETED':
            raise DeserializationError(
                f'Unexpected bitfinex movement with status: {raw_result[5]}. '
                f'Only completed movements are processed. Raw movement: {raw_result}',
            )
        asset = asset_from_bitfinex(bitfinex_name=raw_result[1])

        amount = deserialize_fval(raw_result[12])
        event_type: Final = (
            HistoryEventType.DEPOSIT
            if amount > ZERO
            else HistoryEventType.WITHDRAWAL
        )
        address = None
        transaction_id = None
        if asset.is_fiat() is False:
            address = str(raw_result[16])
            transaction_id = str(raw_result[20])

        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=TimestampMS(deserialize_timestamp(raw_result[5])),
            asset=asset,
            amount=abs(amount),
            fee=AssetAmount(asset=asset, amount=abs(deserialize_fval_or_zero(raw_result[13]))),
            unique_id=(reference := str(raw_result[0])),
            extra_data=maybe_set_transaction_extra_data(
                address=address,
                transaction_id=transaction_id,
                extra_data={'reference': reference},
            ),
        )

    def _deserialize_trade(self, raw_result: list[Any]) -> list[SwapEvent]:
        """Process a trade result from Bitfinex and deserialize it into SwapEvents.

        The base and quote assets are instantiated using the `fee_currency_symbol`
        (from raw_result[10]) over the pair (from raw_result[1]).

        Known pairs format: 'tETHUST', 'tETH:UST'.

        Can raise:
         - DeserializationError.
         - UnknownAsset
         - UnsupportedAsset

        Schema reference in:
        https://docs.bitfinex.com/reference#rest-auth-trades
        """
        bfx_pair = self._process_bfx_pair(raw_result[1])
        if bfx_pair in self.pair_bfx_symbols_map:
            bfx_base_asset_symbol, bfx_quote_asset_symbol = self.pair_bfx_symbols_map[bfx_pair]
        elif len(bfx_pair) == 6:
            # Could not see it in the listed pairs. Probably delisted. Gotta try and figure it out
            # TODO: The whole pair logic in bitfinex seems complicated. Simplify!
            bfx_base_asset_symbol = bfx_pair[:3]
            bfx_quote_asset_symbol = bfx_pair[3:]
        else:
            raise DeserializationError(
                f'Could not deserialize bitfinex trade pair {raw_result[1]}. '
                f'Raw trade: {raw_result}',
            )

        spend, receive = get_swap_spend_receive(
            is_buy=(amount := deserialize_fval(raw_result[4])) >= ZERO,
            base_asset=asset_from_bitfinex(bitfinex_name=bfx_base_asset_symbol),
            quote_asset=asset_from_bitfinex(bitfinex_name=bfx_quote_asset_symbol),
            amount=abs(amount),
            rate=deserialize_price(raw_result[5]),
        )
        return create_swap_events(
            timestamp=deserialize_timestamp_ms_from_intms(raw_result[2]),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=asset_from_bitfinex(bitfinex_name=raw_result[10]),
                amount=abs(deserialize_fval_or_zero(raw_result[9])),
            ),
            location_label=self.name,
            unique_id=str(raw_result[0]),
        )

    @staticmethod
    def _get_error_response_data(response_list: list[Any]) -> ErrorResponseData:
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

    @staticmethod
    def _process_bfx_pair(raw_pair: str) -> str:
        bfx_pair = raw_pair.replace(':', '')
        return bfx_pair.removeprefix('t')

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
                response_list = jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} currencies list returned invalid JSON response. '
                    f'Check further logs',
                )
            else:
                currencies = [
                    currency for currency in response_list[0]
                    if currency not in set(BITFINEX_EXCHANGE_TEST_ASSETS)
                ]

        return CurrenciesResponse(
            success=was_successful,
            response=response,
            currencies=currencies,
        )

    def _query_currency_map(self) -> None:
        """Query the list that maps standard currency symbols with the version
        of the Bitfinex API. If the request is successful and the list format
        as well, insert or ignore the mapping in location_asset_mappings.

        API result format is: [[[<bitfinex_symbol>, <symbol>], ...]]

        May raise:
        - IndexError if the list is empty.
        - RemoteError if the API returns an error response.
        """
        was_successful = True
        response = self._api_query('configs_map_currency_symbol')

        if response.status_code != HTTPStatus.OK:
            was_successful = False
            log.error(f'{self.name} currency map query failed. Check further logs')
        else:
            try:
                response_list = jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} currency map returned invalid JSON response. Check further logs',
                )
            else:  # add the mappings fetched from the API in globalDB, if they are not already there  # noqa: E501
                test_assets = set(BITFINEX_EXCHANGE_TEST_ASSETS)
                bfx_db_serialized = Location.BITFINEX.serialize_for_db()
                bindings = []
                for bfx_symbol, symbol in response_list[0]:
                    if bfx_symbol in test_assets:
                        continue  # skip test assets
                    try:
                        asset = symbol_to_asset_or_token(symbol)
                    except UnknownAsset:
                        log.info(f'Found new asset symbol {bfx_symbol} for {symbol} in Bitfinex. Support for it has to be added.')  # noqa: E501
                        continue  # skip unknown assets

                    bindings.append((
                        bfx_db_serialized,
                        bfx_symbol,
                        asset.serialize(),
                        bfx_db_serialized,
                        bfx_symbol,
                    ))

                # insert the mapping, and skip unsupported assets
                with GlobalDBHandler().conn.write_ctx() as write_cursor:
                    write_cursor.executemany(
                        'INSERT OR IGNORE INTO location_asset_mappings (location, '
                        'exchange_symbol, local_id) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 '
                        'FROM location_unsupported_assets WHERE location=? AND exchange_symbol=?)',
                        bindings,
                    )

        if was_successful is False:
            raise RemoteError(
                f'bitfinex failed to request exchange currency map. '
                f'Response status code: {response.status_code}. '
                f'Response text: {response.text}.',
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
                response_list = jsonloads_list(response.text)
            except JSONDecodeError:
                was_successful = False
                log.error(
                    f'{self.name} exchange pairs list returned invalid JSON response. '
                    f'Check further logs',
                )
            else:
                pairs = [
                    pair for pair in response_list[0]
                    if not pair.startswith(BITFINEX_EXCHANGE_TEST_ASSETS) and
                    not pair.endswith(BITFINEX_EXCHANGE_TEST_ASSETS)
                ]

        return ExchangePairsResponse(
            success=was_successful,
            response=response,
            pairs=pairs,
        )

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key'],
    ) -> tuple[bool, str]:
        ...

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['balances'],
    ) -> ExchangeQueryBalances:
        ...

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['trades', 'asset_movements'],
    ) -> tuple[list['HistoryBaseEntry'], bool]:
        ...

    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key', 'balances', 'trades', 'asset_movements'],
    ) -> tuple[list, bool] | (tuple[bool, str] | ExchangeQueryBalances):
        """This function processes not successful responses for the cases listed
        in `case`.
        """
        try:
            response_list = jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} {case} returned an invalid JSON response: {response.text}.'
            log.error(msg)

            if case in {'validate_api_key', 'balances'}:
                return False, msg
            if case in {'trades', 'asset_movements'}:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying {self.name} {case}: {msg}',
                )
                return [], True

            raise AssertionError(f'Unexpected {self.name} response_case: {case}') from e

        error_data = self._get_error_response_data(response_list)
        if error_data.error_code == API_ERR_AUTH_NONCE_CODE:
            message = API_ERR_AUTH_NONCE_MESSAGE
        # Errors related with the API key return a human readable message
        elif case == 'validate_api_key' and error_data.error_code == API_KEY_ERROR_CODE:
            message = API_KEY_ERROR_MESSAGE
        else:
            # Below any other error not related with the system clock or the API key
            reason = error_data.reason or response.text
            message = (
                f'{self.name} query responded with error status code: {response.status_code} '
                f'and text: {reason}.'
            )
            log.error(message)

        if case in {'validate_api_key', 'balances'}:
            return False, message
        if case in {'trades', 'asset_movements'}:
            self.msg_aggregator.add_error(
                f'Got remote error while querying {self.name} {case}: {message}',
            )
            return [], True

        raise AssertionError(f'Unexpected {self.name} response_case: {case}')

    def first_connection(self) -> None:
        """Request:
        - currencies list: tickers of the supported assets.
        - pairs list: pairs available for trading.
        - currency map: a map between the ticker used by Bitfinex and the
        standard one (outside Bitfinex).

        These data are stored in properties along with `pair_bfx_symbols_map`,
        a dict that maps a pair between the tickers of the base and quote assets.

        May raise RemoteError if any API request fails.
        """
        if self.first_connection_made:
            return

        currencies_response = self._query_currencies()
        if currencies_response.success is False:
            raise RemoteError(
                f'bitfinex failed to request currencies list. '
                f'Response status code: {currencies_response.response.status_code}. '
                f'Response text: {currencies_response.response.text}.',
            )

        exchange_pairs_response = self._query_exchange_pairs()
        if exchange_pairs_response.success is False:
            raise RemoteError(
                f'bitfinex failed to request exchange pairs list. '
                f'Response status code: {exchange_pairs_response.response.status_code}. '
                f'Response text: {exchange_pairs_response.response.text}.',
            )

        self._query_currency_map()
        # Generate a pair - tickers map. Bitfinex test assets have already been
        # removed from both 'pairs' and 'currencies' lists.
        pair_bfx_symbols_map: dict[str, tuple[str, str]] = {}
        for pair in exchange_pairs_response.pairs:
            bfx_pair = self._process_bfx_pair(pair)
            for bfx_symbol in currencies_response.currencies:
                if bfx_pair.startswith(bfx_symbol):
                    bfx_base_asset_symbol = bfx_symbol
                    bfx_quote_asset_symbol = bfx_pair[len(bfx_symbol):]
                elif bfx_pair.endswith(bfx_symbol):
                    bfx_base_asset_symbol = bfx_pair[:-len(bfx_symbol)]
                    bfx_quote_asset_symbol = bfx_symbol
                else:
                    continue

                pair_bfx_symbols_map[bfx_pair] = (bfx_base_asset_symbol, bfx_quote_asset_symbol)

        self.pair_bfx_symbols_map = pair_bfx_symbols_map
        self.first_connection_made = True

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        """Return the account exchange balances on Bitfinex

        The wallets endpoint returns a list where each item is a currency wallet.
        Each currency wallet has type (i.e. exchange, margin, funding), currency,
        balance, etc. Currencies (tickers) are in Bitfinex format and must be
        standardized.

        Endpoint documentation:
        https://docs.bitfinex.com/reference#rest-auth-wallets
        """
        self.first_connection()

        response = self._api_query('wallets')
        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='balances',
            )
            return result, msg
        try:
            response_list = jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON response: {response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        # Wallet items indices
        currency_index = 1
        balance_index = 2
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for wallet in response_list:
            if len(wallet) < API_WALLET_MIN_RESULT_LENGTH:
                log.error(
                    f'Error processing a {self.name} balance result. '
                    f'Found less items than expected',
                    wallet=wallet,
                )
                self.msg_aggregator.add_error(
                    f'Failed to deserialize a {self.name} balance result. '
                    f'Check logs for details. Ignoring it.',
                )
                continue

            if wallet[balance_index] <= 0:
                continue  # bitfinex can show small negative balances for some coins. Ignore

            try:
                asset = asset_from_bitfinex(bitfinex_name=wallet[currency_index])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported {self.name} asset {e.identifier} due to: {e!s}. '
                    f'Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to query USD price: {e!s}. Skipping balance result.',
                )
                continue

            try:
                amount = deserialize_fval(wallet[balance_index])
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to deserialize asset amount due to {e!s}. Skipping balance result.',
                )
                continue

            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance), ''

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Return the Bitfinex asset movements and swap events.

        Endpoint documentation:
        - Asset movements: https://docs.bitfinex.com/reference#rest-auth-movements
        - Trades: https://docs.bitfinex.com/reference#rest-auth-trades

        Returns a tuple containing the list of history events found and the timestamp from which to
        continue querying in subsequent queries (only differs from end_ts when there are errors).
        """
        self.first_connection()
        actual_end_ts = end_ts

        options = {
            'start': start_ts * 1000,
            'end': end_ts * 1000,
            'limit': API_MOVEMENTS_MAX_LIMIT,
        }
        events, with_errors = self._api_query_paginated(
            options=options,
            case='asset_movements',
        )
        if with_errors:  # Movements are not sorted by timestamp so fail the entire range on error.
            return [], start_ts

        options = {
            'start': start_ts * 1000,
            'end': end_ts * 1000,
            'limit': API_TRADES_MAX_LIMIT,
            'sort': API_TRADES_SORTING_MODE,
        }
        swap_events, with_errors = self._api_query_paginated(
            options=options,
            case='trades',
        )
        events.extend(swap_events)
        if with_errors and len(swap_events) != 0:
            # Trades are sorted by timestamp so return the last successful timestamp
            # in order to continue from there in subsequent queries.
            actual_end_ts = ts_ms_to_sec(swap_events[-1].timestamp)

        return events, actual_end_ts

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bitfinex API key is good for usage in rotki.

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

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for bitfinex
