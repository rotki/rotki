import hashlib
import json
import logging
from base64 import b64encode
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, overload

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_gemini
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import (
    SignatureGeneratorMixin,
    deserialize_asset_movement_address,
    get_key_if_has_val,
)
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_movement_event_type,
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class GeminiPermissionError(Exception):
    pass


def gemini_symbol_to_base_quote(symbol: str) -> tuple[AssetWithOracles, AssetWithOracles]:
    """Turns a gemini symbol product into a base/quote asset tuple

    May raise:
    - UnprocessableTradePair if symbol is in unexpected format.
    - UnknownAsset if any of the pair assets are not known to rotki
    """
    if symbol.endswith('perp'):
        raise UnprocessableTradePair(symbol)

    special_cases = {
        'moodengusd': ('solana/token:ED5nyyWEzpPPiWimP8vYm7sD7TD3LAt3Q3gRTWHzPJBY', 'USD'),  # moodeng solana identifier  # noqa: E501
    }
    if symbol in special_cases:
        base, quote = special_cases[symbol]
        return asset_from_gemini(base), asset_from_gemini(quote)

    # from gemini api, quote assets are either:
    # - 5 chars ('rlusd')
    # - 4 chars ('gusd', 'usdt', 'lusd', 'usdc')
    # - 3 chars ('usd', 'btc', etc)
    if len(symbol) >= 5 and symbol[-5:] == 'rlusd':
        split_at = -5
    elif len(symbol) >= 4 and symbol[-4:] in {'gusd', 'usdt', 'paxg', 'usdc'}:
        split_at = -4
    else:
        split_at = -3

    base, quote = symbol[:split_at], symbol[split_at:]
    return asset_from_gemini(base.upper()), asset_from_gemini(quote.upper())


class Gemini(ExchangeInterface, SignatureGeneratorMixin):

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            base_uri: str = 'https://api.gemini.com',
    ):
        super().__init__(
            name=name,
            location=Location.GEMINI,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = base_uri

        self.session.headers.update({
            'Content-Type': 'text/plain',
            'X-GEMINI-APIKEY': self.api_key,
            'Cache-Control': 'no-cache',
            'Content-Length': '0',
        })

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        # If it's the first time, populate the gemini trade symbols
        self._symbols = self._public_api_query('symbols')
        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'X-GEMINI-APIKEY': self.api_key})

        return changed

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Gemini API key is good for usage in rotki

        Makes sure that the following permissions are given to the key:
        - Auditor
        """
        msg = (
            'Provided Gemini API key needs to have "Auditor" permission activated. '
            'Please log into your gemini account and create a key with '
            'the required permissions.'
        )
        try:
            roles = self._private_api_query(endpoint='roles')
        except GeminiPermissionError:
            return False, msg
        except RemoteError as e:
            error = str(e)
            return False, error

        if roles.get('isAuditor', False) is False:
            return False, msg

        return True, ''

    @property
    def symbols(self) -> list[str]:
        self.first_connection()
        return self._symbols

    def _query_continuously(
            self,
            method: Literal['get', 'post'],
            endpoint: str,
            options: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Queries endpoint until anything but 429 is returned

        May raise:
        - RemoteError if something is wrong connecting to the exchange
        """
        v_endpoint = f'/v1/{endpoint}'
        url = f'{self.base_uri}{v_endpoint}'
        retries_left = CachedSettings().get_query_retry_limit()
        retry_limit = CachedSettings().get_query_retry_limit()
        while retries_left > 0:
            if endpoint in {'mytrades', 'balances', 'transfers', 'roles', 'balances/earn'}:
                # private endpoints
                timestamp = str(ts_now_in_ms())
                payload = {'request': v_endpoint, 'nonce': timestamp}
                if options is not None:
                    payload.update(options)
                encoded_payload = json.dumps(payload).encode()
                b64 = b64encode(encoded_payload)
                signature = self.generate_hmac_signature(b64, digest_algorithm=hashlib.sha384)

                self.session.headers.update({
                    'X-GEMINI-PAYLOAD': b64.decode(),
                    'X-GEMINI-SIGNATURE': signature,
                })

            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=GLOBAL_REQUESTS_TIMEOUT,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Gemini {method} query at {url} connection error: {e!s}',
                ) from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                # Backoff a bit by sleeping. Sleep more, the more retries have been made
                gevent.sleep(retry_limit / retries_left)
                retries_left -= 1
            else:
                # get out of the retry loop, we did not get 429 complaint
                break

        return response  # pyright: ignore # we get in the loop at least once

    def _public_api_query(
            self,
            endpoint: str,
    ) -> list[Any]:
        """Performs a Gemini API Query for a public endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        """
        response = self._query_continuously(method='get', endpoint=endpoint)
        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Gemini query at {response.url} responded with error '
                f'status code: {response.status_code} and text: {response.text}',
            )

        try:
            json_ret = jsonloads_list(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Gemini  query at {response.url} '
                f'returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    @overload
    def _private_api_query(
            self,
            endpoint: Literal['roles'],
            options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...

    @overload
    def _private_api_query(
            self,
            endpoint: Literal['balances', 'mytrades', 'transfers', 'balances/earn'],
            options: dict[str, Any] | None = None,
    ) -> list[Any]:
        ...

    def _private_api_query(
            self,
            endpoint: str,
            options: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Performs a Gemini API Query for a private endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        Raises GeminiPermissionError if the API Key does not have sufficient
        permissions for the endpoint
        """
        response = self._query_continuously(method='post', endpoint=endpoint, options=options)
        json_ret: list[Any] | dict[str, Any]
        if response.status_code == HTTPStatus.FORBIDDEN:
            raise GeminiPermissionError(
                f'API key does not have permission for {endpoint}',
            )
        if response.status_code == HTTPStatus.BAD_REQUEST and ('InvalidSignature' in response.text or 'Invalid API key' in response.text):  # noqa: E501
            raise GeminiPermissionError('Invalid API Key or API secret')
            # else let it be handled by the generic non-200 code error below

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Gemini query at {response.url} responded with error '
                f'status code: {response.status_code} and text: {response.text}',
            )

        deserialization_fn: Callable[[str], dict[str, Any]] | Callable[[str], list[Any]]
        deserialization_fn = jsonloads_dict if endpoint == 'roles' else jsonloads_list

        try:
            json_ret = deserialization_fn(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Gemini query at {response.url} '
                f'returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            balances = self._private_api_query('balances')
            balances.extend(self._private_api_query('balances/earn'))
        except (GeminiPermissionError, RemoteError) as e:
            msg = f'Gemini API request failed. {e!s}'
            log.error(msg)
            return None, msg

        main_currency = CachedSettings().main_currency
        returned_balances: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for entry in balances:
            try:
                balance_type = entry['type']
                if balance_type == 'exchange':
                    amount = deserialize_fval(entry['amount'])
                else:  # should be 'Earn'
                    amount = deserialize_fval(entry['balance'])
                # ignore empty balances
                if amount == ZERO:
                    continue

                asset = asset_from_gemini(entry['currency'])
                try:
                    price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing gemini {balance_type} balance result due to '
                        f'inability to query price: {e!s}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] += Balance(
                    amount=amount,
                    value=amount * price,
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found gemini balance result with unsupported '
                    f'asset {e.identifier}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a gemini balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error('Error processing a gemini balance', error=msg)
                continue

        return returned_balances, ''

    def _get_paginated_query(
            self,
            endpoint: Literal['mytrades', 'transfers'],
            start_ts: Timestamp,
            end_ts: Timestamp,
            **kwargs: Any,
    ) -> list[dict]:
        """Gets all possible results of a paginated gemini query"""
        options: dict[str, Any] = {'timestamp': start_ts, **kwargs}
        # set maximum limits per endpoint as per API docs
        if endpoint == 'mytrades':
            # https://docs.gemini.com/rest-api/?python#get-past-trades
            limit = 500
            options['limit_trades'] = limit
        elif endpoint == 'transfers':
            # https://docs.gemini.com/rest-api/?python#transfers
            limit = 50
            options['limit_trades'] = limit
        else:
            raise AssertionError('_get_paginated_query() used with invalid endpoint')
        result = []

        while True:
            single_result = self._private_api_query(
                endpoint=endpoint,
                options=options,
            )
            result.extend(single_result)
            if len(single_result) < limit:
                break
            # Use millisecond timestamp as pagination mechanism for lack of better option
            # Most recent entry is first
            # https://github.com/PyCQA/pylint/issues/4739
            last_ts_ms = single_result[0]['timestampms']
            # also if we are already over the end timestamp stop
            if int(last_ts_ms / 1000) > end_ts:
                break
            options['timestamp'] = last_ts_ms + 1

        # Gemini results have the most recent first, but we want the oldest first.
        result.reverse()
        # If any entry falls outside the end_ts skip it
        checked_result = []
        for entry in result:
            if (entry['timestampms'] / 1000) > end_ts:
                break
            checked_result.append(entry)

        return checked_result

    def _get_trades_for_symbol(
            self,
            symbol: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[dict]:
        try:
            trades = self._get_paginated_query(
                endpoint='mytrades',
                start_ts=start_ts,
                end_ts=end_ts,
                symbol=symbol,
            )
        except GeminiPermissionError as e:
            self.msg_aggregator.add_error(
                f'Got permission error while querying Gemini for trades: {e!s}',
            )
            return []
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Got remote error while querying Gemini for trades: {e!s}',
            )
            return []
        return trades

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Queries gemini for trades. Returns a list of SwapEvents."""
        log.debug('Query gemini trade history', start_ts=start_ts, end_ts=end_ts)
        swap_events = []
        processed_ids = set()
        for symbol in self.symbols:
            gemini_trades = self._get_trades_for_symbol(
                symbol=symbol,
                start_ts=start_ts,
                end_ts=end_ts,
            )
            for entry in gemini_trades:
                try:
                    timestamp = deserialize_timestamp(entry['timestamp'])
                    if timestamp > end_ts:
                        break

                    if (unique_id := str(entry['tid'])) in processed_ids:
                        continue  # Skip already processed trade

                    base, quote = gemini_symbol_to_base_quote(symbol)
                    spend, receive = get_swap_spend_receive(
                        is_buy=deserialize_trade_type_is_buy(entry['type']),
                        base_asset=base,
                        quote_asset=quote,
                        amount=deserialize_fval(entry['amount']),
                        rate=deserialize_price(entry['price']),
                    )
                    swap_events.extend(create_swap_events(
                        timestamp=ts_sec_to_ms(timestamp),
                        location=self.location,
                        spend=spend,
                        receive=receive,
                        fee=AssetAmount(
                            asset=asset_from_gemini(entry['fee_currency']),
                            amount=deserialize_fval_or_zero(entry['fee_amount']),
                        ),
                        location_label=self.name,
                        group_identifier=create_group_identifier_from_unique_id(
                            location=self.location,
                            unique_id=unique_id,
                        ),
                    ))
                    processed_ids.add(unique_id)
                except UnprocessableTradePair as e:
                    self.msg_aggregator.add_warning(
                        f'Found unprocessable Gemini pair {e.pair}. Ignoring the trade.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='trade',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        'Failed to deserialize a gemini trade. '
                        'Check logs for details. Ignoring it.',
                    )
                    log.error(
                        'Error processing a gemini trade.',
                        raw_trade=entry,
                        error=msg,
                    )
                    continue

        return swap_events

    def _query_asset_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Queries Gemini for transfers. Returns a list of AssetMovements."""
        result = self._get_paginated_query(
            endpoint='transfers',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        movements = []
        for entry in result:
            try:
                timestamp = deserialize_timestamp(entry['timestampms'])
                timestamp = Timestamp(int(timestamp / 1000))
                asset = asset_from_gemini(entry['currency'])
                # Gemini does not include withdrawal fees neither in the API nor in their UI
                movement = AssetMovement(
                    location=Location.GEMINI,
                    location_label=self.name,
                    event_type=deserialize_asset_movement_event_type(entry['type']),
                    timestamp=ts_sec_to_ms(timestamp),
                    asset=asset,
                    amount=deserialize_fval_force_positive(entry['amount']),
                    unique_id=str(entry['eid']),
                    extra_data=maybe_set_transaction_extra_data(
                        address=deserialize_asset_movement_address(entry, 'destination', asset),
                        transaction_id=get_key_if_has_val(entry, 'txHash'),
                    ),
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='deposit/withdrawal',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found gemini deposit/withdrawal with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a gemini deposit/withdrawal. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a gemini deposit_withdrawal',
                    asset_movement=entry,
                    error=msg,
                )
                continue

            movements.append(movement)

        return movements

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple['Sequence[HistoryBaseEntry]', Timestamp]:
        events: list[AssetMovement | SwapEvent] = []
        for query_func in (
            self._query_asset_movements,
            self._query_trades,
        ):
            events.extend(query_func(
                start_ts=start_ts,
                end_ts=end_ts,
            ))

        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for gemini
