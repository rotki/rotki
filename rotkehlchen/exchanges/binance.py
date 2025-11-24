import hashlib
import json
import logging
import operator
from collections import defaultdict
from collections.abc import Sequence
from contextlib import suppress
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode
from uuid import uuid4

import gevent
import requests
from rsqlite import IntegrityError

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import BINANCE_MARKETS_KEY
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import BinancePair, MarginPosition
from rotkehlchen.exchanges.exchange import (
    ExchangeInterface,
    ExchangeQueryBalances,
    ExchangeWithExtras,
)
from rotkehlchen.exchanges.utils import (
    SignatureGeneratorMixin,
    deserialize_asset_movement_address,
    get_key_if_has_val,
    query_binance_exchange_pairs,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
    deserialize_timestamp_from_intms,
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
from rotkehlchen.utils.misc import timestamp_to_date, ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Binance launched at 2017-07-14T04:00:00Z (12:00 GMT+8, Beijing Time)
# https://www.binance.com/en/support/articles/115000599831-Binance-Exchange-Launched-Date-Set
BINANCE_LAUNCH_TS: Final = Timestamp(1500001200)
API_TIME_INTERVAL_CONSTRAINT_TS: Final = 7689600  # 89 days

# this determines the length of the data returned, 100 is the maximum value possible.
BINANCE_SIMPLE_EARN_HISTORY_PAGE_SIZE: Final = 100

V3_METHODS: Final = (
    'account',
    'myTrades',
    'openOrders',
    'exchangeInfo',
    'time',
)
PUBLIC_METHODS: Final = ('exchangeInfo', 'time')

# Binance api error codes we check for (all below apis seem to have the same)
# https://binance-docs.github.io/apidocs/spot/en/#error-codes-2
# https://binance-docs.github.io/apidocs/futures/en/#error-codes-2
# https://binance-docs.github.io/apidocs/delivery/en/#error-codes-2
REJECTED_MBX_KEY: Final = -2015


BINANCE_API_TYPE = Literal['api', 'sapi', 'dapi', 'fapi']

BINANCE_BASE_URL: Final = 'binance.com/'
BINANCEUS_BASE_URL: Final = 'binance.us/'

BINANCE_ASSETS_STARTING_WITH_LD: Final = ('LDO',)


class BinancePermissionError(RemoteError):
    """Exception raised when a binance permission problem is detected

    Example is when there is no margin account to query or insufficient api key permissions."""


def trade_from_binance(
        binance_trade: dict,
        binance_symbols_to_pair: dict[str, BinancePair],
        location: Location,
        exchange_name: str,
) -> tuple[str, list[SwapEvent]]:
    """Convert a trade returned from the Binance API into SwapEvents.

    From the official binance api docs (01/09/18):
    https://github.com/binance-exchange/binance-official-api-docs/blob/62ff32d27bb32d9cc74d63d547c286bb3c9707ef/rest-api.md#terminology

    base asset refers to the asset that is the quantity of a symbol.
    quote asset refers to the asset that is the price of a symbol.

    Returns a tuple containing the unique_id and list of SwapEvents for this trade.
    May raise:
        - UnsupportedAsset due to asset_from_binance
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
    """
    if (binance_pair := binance_symbols_to_pair.get(binance_trade['symbol'])) is None:
        raise DeserializationError(
            f'Error reading a {location!s} trade. Could not find '
            f'{binance_trade["symbol"]} in binance_symbols_to_pair',
        )

    spend, receive = get_swap_spend_receive(
        is_buy=binance_trade['isBuyer'],
        base_asset=binance_pair.base_asset,
        quote_asset=binance_pair.quote_asset,
        amount=deserialize_fval(binance_trade['qty']),
        rate=deserialize_price(binance_trade['price']),
    )
    log.debug(
        f'Processing {location!s} Swap',
        timestamp=(timestamp := deserialize_timestamp_ms_from_intms(binance_trade['time'])),
        pair=binance_trade['symbol'],
        spend=spend,
        receive=receive,
        fee=(fee := AssetAmount(
            asset=asset_from_binance(binance_trade['commissionAsset']),
            amount=deserialize_fval_or_zero(binance_trade['commission']),
        )),
    )
    return (unique_id := str(binance_trade['id'])), create_swap_events(
        timestamp=timestamp,
        location=location,
        spend=spend,
        receive=receive,
        fee=fee,
        location_label=exchange_name,
        group_identifier=create_group_identifier_from_unique_id(
            location=location,
            unique_id=unique_id,
        ),
    )


class Binance(ExchangeInterface, ExchangeWithExtras, SignatureGeneratorMixin):
    """This class supports:
      - Binance: when instantiated with default uri, equals BINANCE_BASE_URL.
      - Binance US: when instantiated with uri equals BINANCEUS_BASE_URL.

    Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/

    Binance US exchange api docs:
    https://github.com/binance-us/binance-official-api-docs

    An unofficial python binance package:
    https://github.com/binance-exchange/python-binance/
    """
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            uri: str = BINANCE_BASE_URL,
            binance_selected_trade_pairs: list[str] | None = None,
    ):
        exchange_location = Location.BINANCE
        if uri == BINANCEUS_BASE_URL:
            exchange_location = Location.BINANCEUS

        super().__init__(
            name=name,
            location=exchange_location,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = uri
        self.session.headers.update({
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })
        self.offset_ms = 0
        self.selected_pairs = binance_selected_trade_pairs

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        # If it's the first time, populate the binance pair trade symbols
        # We know exchangeInfo returns a dict
        try:
            self._symbols_to_pair = query_binance_exchange_pairs(location=self.location)
        except InputError as e:
            self.msg_aggregator.add_error(
                f'Binance exchange couldnt be properly initialized. '
                f'Missing the exchange markets. {e!s}',
            )
            self._symbols_to_pair = {}

        server_time = self.api_query_dict('api', 'time')
        self.offset_ms = server_time['serverTime'] - ts_now_in_ms()

        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'X-MBX-APIKEY': credentials.api_key})
        return changed

    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        binance_markets = extras.get(BINANCE_MARKETS_KEY)
        if binance_markets is None:
            return False, 'No binance markets provided'

        # now we can update the account type
        self.selected_pairs = binance_markets
        return True, ''

    @property
    def symbols_to_pair(self) -> dict[str, BinancePair]:
        """Returns binance symbols to pair if in memory otherwise queries binance"""
        self.first_connection()
        return self._symbols_to_pair

    def send_unknown_asset_message(
            self,
            asset_identifier: str,
            details: str,
            location: Location | None = None,
    ) -> None:
        """Override setting the WS message location to Binance for both Binance and BinanceUS
        since they share mappings.
        """
        self._send_unknown_asset_message(
            asset_identifier=asset_identifier,
            details=details,
            location=Location.BINANCE,
        )

    def validate_api_key(self) -> tuple[bool, str]:
        try:
            # We know account endpoint returns a dict
            self.api_query_dict('api', 'account')
        except RemoteError as e:
            error = str(e)
            if 'API-key format invalid' in error:
                return False, 'Provided API Key is in invalid Format'
            if 'Signature for this request is not valid' in error:
                return False, 'Provided API Secret is malformed'
            if 'Invalid API-key, IP, or permissions for action' in error:
                return False, 'API Key does not match the given secret'
            if 'Timestamp for this request was' in error:
                return False, (
                    f'Local system clock is not in sync with {self.name} server. '
                    f"Try syncing your system's clock"
                )
            # else reraise
            raise

        return True, ''

    def api_query(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: dict[str, str | int] | None = None,
            request_options_key: Literal['params', 'data'] = 'params',
            request_method: Literal['GET', 'POST'] = 'GET',
    ) -> list | dict:
        """Performs a binance api query

        May raise:
         - RemoteError
         - BinancePermissionError
        """
        call_options = options.copy() if options else {}
        timeout = (cached_settings := CachedSettings()).get_timeout_tuple()
        tries_left = cached_settings.get_query_retry_limit()
        while True:
            if 'signature' in call_options:
                del call_options['signature']

            is_v3_api_method = api_type == 'api' and method in V3_METHODS
            is_new_futures_api = api_type in {'fapi', 'dapi'}
            api_version = 3  # public methods are v3
            if method not in PUBLIC_METHODS:  # api call needs signature
                if api_type in {'sapi', 'dapi'}:
                    api_version = 1
                elif api_type == 'fapi':
                    api_version = 2
                elif is_v3_api_method:
                    api_version = 3
                else:
                    raise AssertionError(
                        f'Should never get to signed binance api call for '
                        f'api_type: {api_type} and method {method}',
                    )

                # Recommended recvWindows is 5000 but we get timeouts with it
                call_options['recvWindow'] = 10000
                call_options['timestamp'] = str(ts_now_in_ms() + self.offset_ms)
                signature = self.generate_hmac_signature(urlencode(call_options))
                call_options['signature'] = signature

            api_subdomain = api_type if is_new_futures_api else 'api'
            request_url = (
                f'https://{api_subdomain}.{self.uri}{api_type}/v{api_version!s}/{method}'
            )
            log.debug(f'{self.name} API request', request_url=request_url)
            try:
                response = self.session.request(  # type: ignore[misc]  # keyword is a string as typed above
                    method=request_method,
                    url=request_url,
                    timeout=timeout,
                    **{request_options_key: call_options},  # type: ignore[arg-type]  # types are correctly set
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} API request failed due to {e!s}',
                ) from e

            if response.status_code not in {200, 418, 429}:
                code = 'no code found'
                msg = 'no message found'
                with suppress(JSONDecodeError):
                    result = json.loads(response.text)
                    if isinstance(result, dict):
                        code = result.get('code', code)
                        msg = result.get('msg', msg)

                if 'Invalid symbol' in msg and method == 'myTrades':
                    assert options, 'We always provide options for myTrades call'
                    symbol = options.get('symbol', 'no symbol given')
                    # Binance does not return trades for delisted markets. It also may
                    # return a delisted market in the active market endpoints, so we
                    # need to handle it here.
                    log.debug(f'Couldnt query {self.name} trades for {symbol} since its delisted')
                    return []

                exception_class: type[RemoteError | BinancePermissionError]
                if response.status_code == 401 and code == REJECTED_MBX_KEY:
                    # Either API key permission error or if futures/dapi then not enabled yet
                    exception_class = BinancePermissionError
                else:
                    exception_class = RemoteError

                raise exception_class(
                    f'{self.name} API request {response.url} for {method} failed with HTTP status '
                    f'code: {response.status_code}, error code: {code} and error message: {msg}')

            if response.status_code in {418, 429}:
                # Binance has limits and if we hit them we should backoff.
                # A Retry-After header is sent with a 418 or 429 responses and
                # will give the number of seconds required to wait, in the case
                # of a 429, to prevent a ban, or, in the case of a 418, until
                # the ban is over.
                # https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits
                # the Retry-After header is returned but it is always 0. We implement our own
                # backoff logic.
                log.debug(
                    'Rate limited request from binance answered with status code '
                    f'{response.status_code} and headers {response.headers}. '
                    f'Retries left: {tries_left}',
                )
                if tries_left >= 1:
                    backoff_seconds = 10 / tries_left
                    gevent.sleep(backoff_seconds)
                    tries_left -= 1
                    continue

                raise RemoteError(
                    f'{self.name} API request {response.url} for {method} failed with '
                    f'HTTP status code: {response.status_code} after exhausting the retries.',
                )

            # else success
            break

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
            ) from e
        return json_ret

    def api_query_dict(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: dict[str, str | int] | None = None,
    ) -> dict:
        """May raise RemoteError and BinancePermissionError due to api_query"""
        result = self.api_query(api_type, method, options)
        if not isinstance(result, dict):
            error_msg = f'Expected dict but did not get it in {self.name} api response.'
            log.error(f'{error_msg}. Got: {result}')
            raise RemoteError(error_msg)

        return result

    def api_query_list(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: dict[str, str | int] | None = None,
            request_method: Literal['GET', 'POST'] = 'GET',
            request_options_key: Literal['params', 'data'] = 'params',
    ) -> list:
        """May raise RemoteError and BinancePermissionError due to api_query"""
        result = self.api_query(
            api_type=api_type,
            method=method,
            options=options,
            request_method=request_method,
            request_options_key=request_options_key,
        )
        if isinstance(result, dict):
            if 'data' in result:
                result = result['data']
            elif 'rows' in result:
                result = result['rows']
            elif 'total' in result and result['total'] == 0:
                # This is a completely undocumented behavior of their api seen in the wild.
                # At least one endpoint (/sapi/v1/fiat/payments) can omit the data
                # key in the response object instead of returning an empty list like
                # other endpoints.
                # returns this {'code': '000000', 'message': 'success', 'success': True, 'total': 0}  # noqa: E501
                return []

        if not isinstance(result, list):
            error_msg = f'Expected list but did not get it in {self.name} api response.'
            log.error(f'{error_msg}. Got: {result}')
            raise RemoteError(error_msg)

        return result

    def _add_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
            new_balances: list[dict],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Add new balances to balances dict"""
        main_currency = CachedSettings().main_currency
        for entry in new_balances:
            try:
                # force string https://github.com/rotki/rotki/issues/2342
                asset_symbol = str(entry['asset'])
                free = deserialize_fval(entry['free'])
                locked = deserialize_fval(entry['locked'])
            except (KeyError, DeserializationError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}'
                log.error(
                    f'Error while deserializing {self.name} balance entry: {entry}. {msg}. '
                    f'Ignoring its spot/funding balance query.',
                )
                continue

            if asset_symbol.startswith('LD') and asset_symbol not in BINANCE_ASSETS_STARTING_WITH_LD:  # noqa: E501
                # when you receive the interest from your Flexible Earn products,
                # the amount you receive in your Spot wallet is preceded by LD that
                # stands for "Lending Daily". Ignore since we query them from other endpoint
                continue

            if (amount := free + locked) == ZERO:
                continue

            try:
                asset = asset_from_binance(asset_symbol)
            except UnsupportedAsset as e:
                if e.identifier != 'ETF':
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        f'Ignoring its balance query.',
                    )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except DeserializationError:
                log.error(
                    f'Found {self.name} asset with non-string type {type(entry["asset"])}. '
                    f'Ignoring its balance query.',
                )
                continue

            try:
                price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
            except RemoteError as e:
                log.error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query price: {e!s}. Skipping balance entry',
                )
                continue

            balances[asset] += Balance(amount=amount, value=amount * price)

        return balances

    def _query_spot_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        try:
            account_data = self.api_query_dict(api_type='api', method='account')
        except (RemoteError, BinancePermissionError) as e:
            log.warning(
                f'Failed to query {self.name} spot wallet balances.'
                f'Skipping query. Response details: {e!s}',
            )
            return balances

        if (binance_balances := account_data.get('balances', None)) is None:
            raise RemoteError('Binance spot balances response did not contain the balances key')

        return self._add_balances(balances=balances, new_balances=binance_balances)

    def _query_funding_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Query the balances of funding wallet in binance.
        Docs: https://binance-docs.github.io/apidocs/spot/en/#funding-wallet-user_data

        May Raise RemoteError due to api_query or invalid response"""
        try:
            if len(funding_balances := self.api_query_list(
                api_type='sapi',
                method='asset/get-funding-asset',
                request_method='POST',
                request_options_key='data',
            )) == 0:
                return balances
        except (RemoteError, BinancePermissionError) as e:
            log.warning(
                f'Failed to query {self.name} funding wallet balances.'
                f'Skipping query. Response details: {e!s}',
            )
            return balances

        return self._add_balances(balances=balances, new_balances=funding_balances)

    def _query_lending_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Queries binance lending balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        all_positions = []
        timestamp = ts_now_in_ms()
        current = 1
        try:
            while True:  # query all flexible positions
                if len(positions := self.api_query_list(
                    api_type='sapi',
                    method='simple-earn/flexible/position',
                    options={
                        'timestamp': timestamp,
                        'current': current,
                        'size': BINANCE_SIMPLE_EARN_HISTORY_PAGE_SIZE,
                    },
                )) > 0:
                    all_positions.append(('totalAmount', positions))
                    current += 1
                else:
                    break

            current = 1
            while True:  # query all locked position
                if len(positions := self.api_query_list(
                    api_type='sapi',
                    method='simple-earn/locked/position',
                    options={
                        'timestamp': timestamp,
                        'current': current,
                        'size': BINANCE_SIMPLE_EARN_HISTORY_PAGE_SIZE,
                    },
                )) > 0:
                    all_positions.append(('amount', positions))
                    current += 1
                else:
                    break
        except RemoteError as e:
            raise RemoteError(
                f'Could not query simple earn account balances at {timestamp}. {e!s}',
            ) from e

        main_currency = CachedSettings().main_currency
        for amount_key, positions in all_positions:
            for entry in positions:
                try:
                    amount = deserialize_fval(entry[amount_key])
                    if amount == ZERO:
                        continue

                    asset = asset_from_binance(entry['asset'])
                except UnsupportedAsset as e:
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        'Ignoring its lending balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='lending balance query',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    log.error(
                        f'Error at deserializing {self.name} asset. {msg}. '
                        f'Ignoring its lending balance query.',
                    )
                    continue

                try:
                    price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
                except RemoteError as e:
                    log.error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query price: {e!s}. Skipping balance entry',
                    )
                    continue

                balances[asset] += Balance(
                    amount=amount,
                    value=amount * price,
                )

        return balances

    def query_lending_interests_history(
            self,
            cursor: 'DBCursor',
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> bool:
        """Queries Binance Simple Earn history, transforms it into `HistoryEvent` objects
        and saves it in the database.

        "BONUS" -> Bonus tiered APR.
        "REALTIME" -> Real-time APR.
        "REWARDS" -> Historical rewards.

        `end_ts` - `start_ts` <= 89 days. This is handled using `_api_query_list_within_time_delta`
        using `API_TIME_INTERVAL_CONSTRAINT_TS` as the timedelta.

        Lending Interest History Documentation:
        https://binance-docs.github.io/apidocs/spot/en/#get-flexible-rewards-history-user_data
        https://binance-docs.github.io/apidocs/spot/en/#get-locked-rewards-history-user_data

        May raise:
        - RemoteError
        - BinancePermissionError

        Returns True if there is an error, otherwise returns False.
        """
        if self.location == Location.BINANCEUS:
            log.debug('Skipping query of simple earn history as Binance US does not support it.')
            return False

        ranges = DBQueryRanges(self.db)
        history_events_db = DBHistoryEvents(self.db)

        # Query and save flexible simple earn history
        range_query_name = f'{self.location}_lending_history_{self.name}'
        ranges_to_query = ranges.get_location_query_ranges(
            cursor=cursor,
            location_string=range_query_name,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        for query_start_ts, query_end_ts in ranges_to_query:
            for lending_type in ('BONUS', 'REALTIME', 'REWARDS'):
                try:
                    response = self._api_query_list_within_time_delta(
                        api_type='sapi',
                        start_ts=query_start_ts,
                        time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                        end_ts=query_end_ts,
                        method='simple-earn/flexible/history/rewardsRecord',
                        additional_options={
                            'type': lending_type,
                            'size': BINANCE_SIMPLE_EARN_HISTORY_PAGE_SIZE,
                        },
                    )
                except (RemoteError, BinancePermissionError) as e:
                    self.msg_aggregator.add_error(
                        f'Failed to query binance flexible lending interest history between '
                        f'{timestamp_to_date(query_start_ts)} and '
                        f'{timestamp_to_date(query_end_ts)}. {e!s}',
                    )
                    return True

                for entry in response:
                    try:
                        interest_received = deserialize_fval(entry['rewards'])
                        if interest_received == ZERO:
                            continue

                        timestamp = TimestampMS(entry['time'])
                        notes = f'Interest paid from {entry["type"]} {entry["asset"]} savings'
                    except KeyError as e:
                        self.msg_aggregator.add_error(
                            f'Missing key entry for {e!s} in {self.name} {entry}. '
                            f'Ignoring its lending interest history query.',
                        )
                        continue
                    except DeserializationError as e:
                        self.msg_aggregator.add_error(
                            f'Error at deserializing {self.name} asset. {e!s}. '
                            f'Ignoring its lending interest history query.',
                        )
                        continue

                    try:
                        asset = asset_from_binance(entry['asset'])
                    except UnsupportedAsset as e:
                        log.error(
                            f'Found unsupported {self.name} asset {e.identifier}. '
                            f'Ignoring its lending interest history query.',
                        )
                        continue
                    except UnknownAsset as e:
                        self.send_unknown_asset_message(
                            asset_identifier=e.identifier,
                            details='lending interest history query',
                        )
                        continue

                    event = HistoryEvent(
                        group_identifier=hashlib.sha256(str(entry).encode()).hexdigest(),  # entry hash  # noqa: E501
                        sequence_index=0,  # since group_identifier is always different
                        timestamp=timestamp,
                        location=self.location,
                        location_label=self.name,  # the name of the CEX instance
                        asset=asset,
                        amount=interest_received,
                        notes=notes,
                        event_type=HistoryEventType.RECEIVE,
                        event_subtype=HistoryEventSubType.REWARD,
                    )

                    with self.db.user_write() as write_cursor:
                        try:
                            history_events_db.add_history_event(write_cursor, event)
                        except (IntegrityError, DeserializationError) as e:
                            log.error(f'Did not add lending history event {event} to the DB due to {e!s}')  # noqa: E501

        # Query and save locked simple earn history
        for query_start_ts, query_end_ts in ranges_to_query:
            try:
                response = self._api_query_list_within_time_delta(
                    api_type='sapi',
                    start_ts=query_start_ts,
                    time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                    end_ts=query_end_ts,
                    method='simple-earn/locked/history/rewardsRecord',
                    additional_options={'size': BINANCE_SIMPLE_EARN_HISTORY_PAGE_SIZE},
                )
            except (RemoteError, BinancePermissionError) as e:
                self.msg_aggregator.add_error(
                    f'Failed to query binance locked lending interest history between '
                    f'{timestamp_to_date(query_start_ts)} and '
                    f'{timestamp_to_date(query_end_ts)}. {e!s}',
                )
                return True

            for entry in response:
                try:
                    interest_received = deserialize_fval(entry['amount'])
                    if interest_received == ZERO:
                        continue

                    timestamp = TimestampMS(entry['time'])
                    notes = f'Interest paid from locked {entry["asset"]} savings'
                except KeyError as e:
                    self.msg_aggregator.add_error(
                        f'Missing key entry for {e!s} in {self.name} {entry}. '
                        f'Ignoring its lending interest history query.',
                    )
                    continue
                except DeserializationError as e:
                    self.msg_aggregator.add_error(
                        f'Error at deserializing {self.name} asset. {e!s}. '
                        f'Ignoring its lending interest history query.',
                    )
                    continue

                try:
                    asset = asset_from_binance(entry['asset'])
                except UnsupportedAsset as e:
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        f'Ignoring its lending interest history query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='lending interest history query',
                    )
                    continue

                event = HistoryEvent(
                    group_identifier=hashlib.sha256(str(entry).encode()).hexdigest(),  # entry hash
                    sequence_index=0,  # since group_identifier is always different
                    timestamp=timestamp,
                    location=self.location,
                    location_label=self.name,  # the name of the CEX instance
                    asset=asset,
                    amount=interest_received,
                    notes=notes,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.REWARD,
                )

                with self.db.user_write() as write_cursor:
                    try:
                        history_events_db.add_history_event(write_cursor, event)
                    except (IntegrityError, DeserializationError) as e:
                        log.error(f'Did not add lending history event {event} to the DB due to {e!s}')  # noqa: E501

            with self.db.user_write() as write_cursor:
                ranges.update_used_query_range(
                    write_cursor=write_cursor,
                    location_string=range_query_name,
                    queried_ranges=[(query_start_ts, query_end_ts)],
                )

        return False

    def _query_cross_collateral_futures_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Queries binance collateral future balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        futures_response = self.api_query_dict('sapi', 'futures/loan/wallet')
        main_currency = CachedSettings().main_currency
        try:
            cross_collaterals = futures_response['crossCollaterals']
            for entry in cross_collaterals:
                amount = deserialize_fval(entry['locked'])
                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_binance(entry['collateralCoin'])
                except UnsupportedAsset as e:
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        f'Ignoring its futures balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='futures balance query',
                    )
                    continue
                except DeserializationError:
                    log.error(
                        f'Found {self.name} asset with non-string type '
                        f'{type(entry["asset"])}. Ignoring its futures balance query.',
                    )
                    continue

                try:
                    price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
                except RemoteError as e:
                    log.error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query price: {e!s}. Skipping balance entry',
                    )
                    continue

                balances[asset] += Balance(
                    amount=amount,
                    value=amount * price,
                )

        except KeyError as e:
            self.msg_aggregator.add_error(
                f'At {self.name} futures balance query did not find expected key '
                f'{e!s}. Skipping futures query...',
            )

        return balances

    def _query_margined_fapi(self, balances: defaultdict[AssetWithOracles, Balance]) -> defaultdict[AssetWithOracles, Balance]:  # noqa: E501
        """Only a convenience function to give same interface as other query methods"""
        return self._query_margined_futures_balances('fapi', balances)

    def _query_margined_dapi(self, balances: defaultdict[AssetWithOracles, Balance]) -> defaultdict[AssetWithOracles, Balance]:  # noqa: E501
        """Only a convenience function to give same interface as other query methods"""
        return self._query_margined_futures_balances('dapi', balances)

    def _query_margined_futures_balances(
            self,
            api_type: Literal['fapi', 'dapi'],
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Queries binance margined future balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        try:
            response = self.api_query_list(api_type, 'balance')
        except BinancePermissionError as e:
            log.warning(
                f'Insufficient permission to query {self.name} {api_type} balances.'
                f'Skipping query. Response details: {e!s}',
            )
            return balances

        main_currency = CachedSettings().main_currency
        try:
            for entry in response:
                amount = deserialize_fval(entry['balance'])
                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_binance(entry['asset'])
                except UnsupportedAsset as e:
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        f'Ignoring its margined futures balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='margined futures balance query',
                    )
                    continue
                except DeserializationError:
                    log.error(
                        f'Found {self.name} asset with non-string type '
                        f'{type(entry["asset"])}. Ignoring its margined futures balance query.',
                    )
                    continue

                try:
                    price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
                except RemoteError as e:
                    log.error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query price: {e!s}. Skipping margined futures balance entry',
                    )
                    continue

                balances[asset] += Balance(
                    amount=amount,
                    value=amount * price,
                )

        except KeyError as e:
            self.msg_aggregator.add_error(
                f'At {self.name} margin futures balance query did not find '
                f'expected key {e!s}. Skipping margin futures query...',
            )

        return balances

    def _query_pools_balances(
            self,
            balances: defaultdict[AssetWithOracles, Balance],
    ) -> defaultdict[AssetWithOracles, Balance]:
        """Queries binance pool balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        main_currency = CachedSettings().main_currency

        def process_pool_asset(asset_name: str, asset_amount: FVal) -> None:
            if asset_amount == ZERO:
                return None

            try:
                asset = asset_from_binance(asset_name)
            except UnsupportedAsset as e:
                log.error(
                    f'Found unsupported {self.name} asset {asset_name}. '
                    f'Ignoring its {self.name} pool balance query. {e!s}',
                )
                return None
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='pool balance query',
                )
                return None
            except DeserializationError as e:
                log.error(
                    f'{self.name} balance deserialization error '
                    f'for asset {asset_name}: {e!s}. Skipping entry.',
                )
                return None

            try:
                price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
            except RemoteError as e:
                log.error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query price: {e!s}. Skipping {self.name} pool balance entry',
                )
                return None

            balances[asset] += Balance(
                amount=asset_amount,
                value=asset_amount * price,
            )
            return None

        try:
            response = self.api_query('sapi', 'bswap/liquidity')
        except BinancePermissionError as e:
            log.warning(
                f'Insufficient permission to query {self.name} pool balances.'
                f'Skipping query. Response details: {e!s}',
            )
            return balances

        try:
            for entry in response:
                for asset_name, asset_amount in entry['share']['asset'].items():
                    process_pool_asset(asset_name, FVal(asset_amount))
        except (KeyError, AttributeError) as e:
            self.msg_aggregator.add_error(
                f'At {self.name} pool balances got unexpected data format. '
                f'Skipping them in the balance query. Check logs for details',
            )
            if isinstance(e, KeyError):
                msg = f'Missing key {e!s}'
            else:
                msg = str(e)
            log.error(
                f'Unexpected data format returned by {self.name} pools. '
                f'Data: {response}. Error: {msg}',
            )

        return balances

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            self.first_connection()
            returned_balances: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
            returned_balances = self._query_spot_balances(returned_balances)
            returned_balances = self._query_funding_balances(returned_balances)
            if self.location != Location.BINANCEUS:
                for method in (
                        self._query_lending_balances,
                        self._query_cross_collateral_futures_balances,
                        self._query_margined_fapi,
                        self._query_margined_dapi,
                        self._query_pools_balances,
                ):
                    try:
                        returned_balances = method(returned_balances)
                    except RemoteError as e:  # errors in any of these methods should not be fatal
                        log.warning(f'Failed to query binance method {method.__name__} due to {e!s}')  # noqa: E501

        except RemoteError as e:
            msg = (
                f'{self.name} account API request failed. '
                f'Could not reach binance due to {e!s}'
            )
            self.msg_aggregator.add_error(msg)
            return None, msg

        log.debug(
            f'{self.name} balance query result',
            balances=returned_balances,
        )
        return dict(returned_balances), ''

    def _query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> list[SwapEvent]:
        """
        For trades coming from api/myTrades this function won't respect the provided range and
        will always query all the trades until now. The reason is that binance forces us to query
        all the pairs and we use the cache at BINANCE_PAIR_LAST_ID to remember which one was the
        last trade queried on each market speeding up the queries. For fiat payments the time
        range is respected.

        May raise due to api query, unexpected id, or missing market pairs:
        - RemoteError
        - BinancePermissionError
        - InputError
        """
        self.first_connection()
        if self.selected_pairs is None or len(self.selected_pairs) == 0:
            self.msg_aggregator.add_message(
                message_type=WSMessageType.BINANCE_PAIRS_MISSING,
                data={'location': self.location, 'name': self.name},
            )
            raise InputError(f'Cannot query {self.name} trade history with no market pairs selected.')  # noqa: E501

        iter_markets = list(set(self.selected_pairs).intersection(set(self._symbols_to_pair.keys())))  # noqa: E501
        log.debug(f'Will query the following binance markets: {iter_markets}')
        raw_data = []
        # Limit of results to return. 1000 is max limit according to docs
        limit = 1000
        for symbol in iter_markets:
            if force_refresh:
                last_trade_id = 0  # Bypass cache when force_refresh is True
            else:
                with self.db.conn.read_ctx() as cursor:
                    last_trade_id = self.db.get_dynamic_cache(  # api returns trades with id >= last_trade_id  # noqa: E501
                        cursor=cursor,
                        name=DBCacheDynamic.BINANCE_PAIR_LAST_ID,
                        location=self.location.serialize(),
                        location_name=self.name,
                        queried_pair=symbol,
                    ) or 0

            log.debug(
                f'Will query binance trades on {self.name} for {symbol=} after {last_trade_id=}',
            )
            len_result = limit
            while len_result == limit:
                # We know that myTrades returns a list from the api docs
                result = self.api_query_list(
                    'api',
                    'myTrades',
                    options={
                        'symbol': symbol,
                        'fromId': last_trade_id,
                        'limit': limit,
                        # Not specifying them since binance does not seem to
                        # respect them and always return all trades
                    })
                if result:
                    try:
                        last_trade_id = int(result[-1]['id']) + 1
                    except (ValueError, KeyError, IndexError) as e:
                        raise RemoteError(
                            f'Could not parse id from Binance myTrades api query result: {result}',
                        ) from e

                len_result = len(result)
                log.debug(f'{self.name} myTrades query result', results_num=len_result)
                for r in result:
                    r['symbol'] = symbol
                raw_data.extend(result)

            raw_data.sort(key=operator.itemgetter('time'))

        events: list[SwapEvent] = []
        last_pair_to_tradeid: dict[str, str] = {}
        for raw_trade in raw_data:
            try:
                trade_pair = raw_trade['symbol']
                unique_id, swap_events = trade_from_binance(
                    binance_trade=raw_trade,
                    binance_symbols_to_pair=self.symbols_to_pair,
                    exchange_name=self.name,
                    location=self.location,
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='trade',
                )
                continue
            except UnsupportedAsset as e:
                log.error(
                    f'Found {self.name} trade with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error processing a {self.name} trade. Check logs '
                    f'for details. Ignoring it.',
                )
                log.error(
                    f'Error processing a {self.name} trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue

            # trades are ordered in asc order by us
            last_pair_to_tradeid[trade_pair] = unique_id
            events.extend(swap_events)

        if not force_refresh:  # Only update cache when not forcing refresh
            with self.db.conn.write_ctx() as write_cursor:
                for symbol, unique_id in last_pair_to_tradeid.items():
                    self.db.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.BINANCE_PAIR_LAST_ID,
                        value=int(unique_id),
                        location=self.location.serialize(),
                        location_name=self.name,
                        queried_pair=symbol,
                    )

        fiat_payments = self._query_online_fiat_payments(start_ts=start_ts, end_ts=end_ts)
        if fiat_payments:
            events.extend(fiat_payments)
            events.sort(key=lambda x: x.timestamp)

        return events

    def _query_online_fiat_payments(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        if self.location == Location.BINANCEUS:
            return []  # dont exist for Binance US: https://github.com/rotki/rotki/issues/3664

        fiat_buys = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='fiat/payments',
            additional_options={'transactionType': 0},
        )
        log.debug(f'{self.name} fiat buys history result', results_num=len(fiat_buys))
        fiat_sells = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='fiat/payments',
            additional_options={'transactionType': 1},
        )
        log.debug(f'{self.name} fiat sells history result', results_num=len(fiat_sells))

        events = []
        for is_buy, fiat_events in (
            (True, fiat_buys),
            (False, fiat_sells),
        ):
            for raw_fiat in fiat_events:
                events.extend(self._deserialize_fiat_payment(
                    raw_data=raw_fiat,
                    is_buy=is_buy,
                ))

        return events

    def _deserialize_fiat_payment(
            self,
            raw_data: dict[str, Any],
            is_buy: bool,
    ) -> list[SwapEvent]:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return an empty list if something went wrong at deserialization
        """
        try:
            if 'status' not in raw_data or raw_data['status'] != 'Completed':
                log.error(f'Found {self.location!s} fiat payment with failed status. Ignoring it.')
                return []

            spend, receive = get_swap_spend_receive(
                is_buy=is_buy,
                base_asset=asset_from_binance(raw_data['cryptoCurrency']),
                quote_asset=(fiat_asset := asset_from_binance(raw_data['fiatCurrency'])),
                amount=deserialize_fval_force_positive(raw_data['obtainAmount']),
                rate=deserialize_price(raw_data['price']),
            )
            unique_id = get_key_if_has_val(raw_data, 'orderNo')
            return create_swap_events(
                timestamp=deserialize_timestamp_ms_from_intms(raw_data['createTime']),
                location=self.location,
                spend=spend,
                receive=receive,
                fee=AssetAmount(
                    asset=fiat_asset,
                    amount=deserialize_fval(raw_data['totalFee']),
                ),
                location_label=self.name,
                group_identifier=create_group_identifier_from_unique_id(
                    location=self.location,
                    unique_id=unique_id,
                ) if unique_id else f'{uuid4().hex}',
            )
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='fiat payment',
            )
        except UnsupportedAsset as e:
            log.error(
                f'Found {self.location!s} fiat payment with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {self.location!s} fiat payment. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {self.location!s} fiat payment',
                asset_movement=raw_data,
                error=msg,
            )

        return []

    def _deserialize_fiat_movement(
            self,
            raw_data: dict[str, Any],
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list[AssetMovement] | None:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if 'status' not in raw_data or raw_data['status'] not in {'Successful', 'Finished'}:
                log.error(
                    f'Found {self.location!s} fiat deposit/withdrawal with failed status. Ignoring it.',  # noqa: E501
                )
                return None

            asset = asset_from_binance(raw_data['fiatCurrency'])
            tx_id = get_key_if_has_val(raw_data, 'orderNo')
            timestamp = ts_sec_to_ms(deserialize_timestamp_from_intms(raw_data['createTime']))
            fee = deserialize_fval(raw_data['totalFee'])
            amount = deserialize_fval_force_positive(raw_data['amount'])
            address = deserialize_asset_movement_address(raw_data, 'address', asset)
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='fiat deposit/withdrawal',
            )
        except UnsupportedAsset as e:
            log.error(
                f'Found {self.location!s} fiat deposit/withdrawal with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {self.location!s} fiat deposit/withdrawal. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {self.location!s} fiat deposit/withdrawal',
                asset_movement=raw_data,
                error=msg,
            )
        else:
            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_type=event_type,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=AssetAmount(asset=asset, amount=fee),
                unique_id=tx_id,
                extra_data=maybe_set_transaction_extra_data(
                    address=address,
                    transaction_id=tx_id,
                ),
            )

        return None

    def _deserialize_asset_movement(self, raw_data: dict[str, Any]) -> list[AssetMovement] | None:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
            if 'insertTime' in raw_data:
                event_type = HistoryEventType.DEPOSIT
                timestamp = ts_sec_to_ms(deserialize_timestamp_from_intms(raw_data['insertTime']))
                fee = ZERO
            else:
                event_type = HistoryEventType.WITHDRAWAL
                timestamp = ts_sec_to_ms(deserialize_timestamp_from_date(
                    date=raw_data['applyTime'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='binance withdrawal',
                    skip_milliseconds=True,
                ))
                fee = deserialize_fval(raw_data['transactionFee'])

            asset = asset_from_binance(raw_data['coin'])
            tx_id = get_key_if_has_val(raw_data, 'txId')
            internal_id = get_key_if_has_val(raw_data, 'id')
            unique_id = str(internal_id) if internal_id else str(tx_id) if tx_id else ''
            address = deserialize_asset_movement_address(raw_data, 'address', asset)
            amount = deserialize_fval_force_positive(raw_data['amount'])
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='deposit/withdrawal',
            )
        except UnsupportedAsset as e:
            log.error(
                f'Found {self.location!s} deposit/withdrawal with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {self.location!s} deposit/withdrawal. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {self.location!s} deposit/withdrawal',
                asset_movement=raw_data,
                error=msg,
            )
        else:
            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_type=event_type,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=AssetAmount(asset=asset, amount=fee),
                unique_id=unique_id,
                extra_data=maybe_set_transaction_extra_data(
                    address=address,
                    transaction_id=tx_id,
                ),
            )

        return None

    def _api_query_list_within_time_delta(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            time_delta: int,
            api_type: BINANCE_API_TYPE,
            method: Literal[
                'capital/deposit/hisrec',
                'capital/withdraw/history',
                'fiat/orders',
                'fiat/payments',
                'simple-earn/flexible/history/rewardsRecord',
                'simple-earn/locked/history/rewardsRecord',
            ],
            additional_options: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Request via `api_query_dict()` from `start_ts` `end_ts` using a time
        delta (offset) less than `time_delta`.

        Be aware of:
          - If `start_ts` equals zero, the Binance launch timestamp is used
          (from BINANCE_LAUNCH_TS). This value is not stored in the
          `used_query_ranges` table, but 0.
          - Timestamps are converted to milliseconds.
        """
        results: list[dict[str, Any]] = []
        # Create required time references in milliseconds
        start_ts = Timestamp(start_ts * 1000)
        end_ts = Timestamp(end_ts * 1000)
        offset = time_delta * 1000 - 1  # less than time_delta
        if start_ts == Timestamp(0):
            from_ts = BINANCE_LAUNCH_TS * 1000
        else:
            from_ts = start_ts

        to_ts = (
            from_ts + offset  # Case request with offset
            if end_ts - from_ts > offset
            else end_ts  # Case request without offset (1 request)
        )
        while True:
            options: dict[str, int | str] = {
                'timestamp': ts_now_in_ms(),
                'startTime': from_ts,
                'endTime': to_ts,
            }
            if additional_options:
                options.update(additional_options)

            results.extend(self.api_query_list(api_type, method, options=options))

            # Case stop requesting
            if to_ts >= end_ts:
                break

            from_ts = to_ts + 1
            to_ts = min(to_ts + offset, end_ts)

        return results

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        events: list[HistoryBaseEntry] = []
        for query_func in (
            self._query_online_asset_movements,
            self._query_online_trade_history,
        ):
            try:
                events.extend(query_func(start_ts=start_ts, end_ts=end_ts, force_refresh=force_refresh))  # noqa: E501
            except (RemoteError, BinancePermissionError) as e:
                log.error(
                    f'Failed to call {self.name} {query_func.__name__} '
                    f'between {start_ts} and {end_ts} due to {e!s}',
                )
                continue

        return events, end_ts

    def _query_online_asset_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,  # no-op for asset movements.
    ) -> Sequence[HistoryBaseEntry]:
        """
        Be aware of:
          - Timestamps must be in milliseconds.
          - There must be less than 90 days between start and end timestamps.

        Deposit & Withdraw history documentation:
        https://binance-docs.github.io/apidocs/spot/en/#deposit-history-user_data
        https://binance-docs.github.io/apidocs/spot/en/#withdraw-history-user_data
        """
        deposits = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='capital/deposit/hisrec',
        )
        log.debug(f'{self.name} deposit history result', results_num=len(deposits))

        withdraws = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='capital/withdraw/history',
        )
        log.debug(f'{self.name} withdraw history result', results_num=len(withdraws))

        if self.location != Location.BINANCEUS:
            # dont exist for Binance US: https://github.com/rotki/rotki/issues/3664
            fiat_deposits = self._api_query_list_within_time_delta(
                start_ts=start_ts,
                end_ts=end_ts,
                time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                api_type='sapi',
                method='fiat/orders',
                additional_options={'transactionType': 0},
            )
            log.debug(f'{self.name} fiat deposit history result', results_num=len(fiat_deposits))
            fiat_withdraws = self._api_query_list_within_time_delta(
                start_ts=start_ts,
                end_ts=end_ts,
                time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                api_type='sapi',
                method='fiat/orders',
                additional_options={'transactionType': 1},
            )
            log.debug(f'{self.name} fiat withdraw history result', results_num=len(fiat_withdraws))
        else:
            fiat_deposits, fiat_withdraws = [], []

        movements = []
        for raw_movement in deposits + withdraws:
            movement = self._deserialize_asset_movement(raw_movement)
            if movement:
                movements.extend(movement)

        for idx, fiat_movement in enumerate(fiat_deposits + fiat_withdraws):
            movement = self._deserialize_fiat_movement(
                raw_data=fiat_movement,
                event_type=HistoryEventType.DEPOSIT if idx < len(fiat_deposits) else HistoryEventType.WITHDRAWAL,  # noqa: E501
            )
            if movement:
                movements.extend(movement)

        return movements

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for binance
