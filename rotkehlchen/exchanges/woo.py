import logging
import urllib
from collections import defaultdict
from collections.abc import Callable, Sequence
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_woo
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_floatstr,
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

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

API_KEY_ERROR_CODE_ACTION: dict = {
    '-1000': 'An unknown error occurred while processing the request.',
    '-1001': 'The api key or secret is in wrong format.',
    '-1002': 'The api key or secret is invalid.',
}
API_MAX_LIMIT = 1000  # Max limit for all API v1 endpoints
MIN_TIMESTAMP = Timestamp(1000000000)  # minimum timestamp that can be queried as per woo docs


class TradePairData(NamedTuple):
    pair: str
    base_asset_symbol: str
    quote_asset_symbol: str
    base_asset: AssetWithOracles
    quote_asset: AssetWithOracles


class Woo(ExchangeInterface, SignatureGeneratorMixin):
    """Woo exchange api docs: https://docs.woo.org/#general-information"""
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
            location=Location.WOO,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = 'https://api.woo.org'
        # NB: x-api-signature & x-api-timestamp change per request
        # x-api-key is constant
        self.session.headers.update({
            'x-api-key': self.api_key,
        })

    def first_connection(self) -> None:
        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'x-api-key': credentials.api_key})
        return changed

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        """
        Return the account balances on Woo.

        May raise:
        - Remote Error
        """
        response = self._api_query('v3/balances')
        try:
            balances = response['data']['holding']
        except KeyError as e:
            msg = f'Woo balances JSON response is missing the key {e}'
            log.error(msg, response)
            raise RemoteError(msg) from e

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for entry in balances:
            try:
                if (amount := deserialize_fval(entry['holding'] + entry['staked'])) == ZERO:
                    continue
                asset = asset_from_woo(entry['token'])
                usd_price = Inquirer.find_usd_price(asset=asset)
            except (DeserializationError, KeyError) as e:
                log.error('Error processing a Woo balance.', entry=entry, error=str(e))
                self.msg_aggregator.add_error(
                    'Failed to deserialize a Woo balance entry.'
                    'Check logs for details. Ignoring it.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Woo balance result due to inability to '
                    f'query USD price: {e}. Skipping balance entry.',
                )
                continue
            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance), ''

    def _deserialize_trade(self, trade: dict[str, Any]) -> list[SwapEvent]:
        """
        Deserialize a Woo trade returned from the API

        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        symbol = trade['symbol']
        try:
            _, base_asset_symbol, quote_asset_symbol = symbol.split('_')
        except ValueError as e:
            raise DeserializationError(
                f'Could not split symbol {symbol} into base and quote asset',
            ) from e

        spend, receive = get_swap_spend_receive(
            is_buy=deserialize_trade_type_is_buy(trade['side']),
            base_asset=asset_from_woo(base_asset_symbol),
            quote_asset=asset_from_woo(quote_asset_symbol),
            amount=deserialize_fval(trade['executed_quantity']),
            rate=deserialize_price(trade['executed_price']),
        )
        return create_swap_events(
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_floatstr(trade['executed_timestamp'])),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=asset_from_woo(trade['fee_asset']),
                amount=deserialize_fval_or_zero(trade['fee']),
            ),
            location_label=self.name,
            event_identifier=create_event_identifier_from_unique_id(
                location=self.location,
                unique_id=str(trade['id']),
            ),
        )

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Return deposits/withdrawals history on Woo in a range of time."""
        events: list[AssetMovement | SwapEvent] = []
        events.extend(self._api_query_paginated(
            endpoint='v1/asset/history',
            options={
                'end_t': (end_ts_ms := ts_sec_to_ms(max(end_ts, MIN_TIMESTAMP))),
                'page': 1,
                'size': API_MAX_LIMIT,
                'start_t': (start_ts_ms := ts_sec_to_ms(max(start_ts, MIN_TIMESTAMP))),
                'status': 'COMPLETED',
                'type': 'BALANCE',
            },
            deserialization_method=self._deserialize_asset_movement,
            entries_key='rows',
        ))
        events.extend(self._api_query_paginated(
            endpoint='v1/client/hist_trades',
            options={
                'end_t': end_ts_ms,
                'fromId': 1,
                'limit': API_MAX_LIMIT,
                'start_t': start_ts_ms,
            },
            deserialization_method=self._deserialize_trade,
            entries_key='data',
        ))
        return events, end_ts

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Woo API key is good for usage in rotki"""
        try:
            self._api_query('v1/client/trades', options={'limit': 1})
        except RemoteError as e:
            return False, str(e)
        return True, ''

    def _api_query(
            self,
            endpoint: str,
            method: Literal['GET', 'POST'] = 'GET',
            options: dict[str, Any] | None = None,
    ) -> dict:
        """
        Query a  Woo API endpoint

        May Raise:
        - RemoteError
        """
        call_options = options or {}
        request_url = f'{self.base_uri}/{endpoint}'
        timestamp = str(ts_now_in_ms())
        parameters = urllib.parse.urlencode(call_options)
        normalized_content = f'{timestamp}{method}/{endpoint}{parameters}' if endpoint.startswith('v3') else f'{parameters}|{timestamp}'  # noqa: E501
        signature = self.generate_hmac_signature(normalized_content)
        self.session.headers.update({
            'x-api-signature': signature,
            'x-api-timestamp': timestamp,
        })
        log.debug('Woo API request', request_url=request_url, options=options)
        error_prefix = f'Woo {method} request at {request_url}'
        try:
            response = self.session.request(
                method=method,
                url=request_url,
                data=call_options if method == 'POST' else {},
                params=call_options if method == 'GET' else {},
                headers=self.session.headers,
            )
            response_dict: dict = response.json()
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'{error_prefix} connection error: {e}.') from e
        except JSONDecodeError as e:
            raise RemoteError(
                f'{error_prefix} failed to decode JSON response.',
            ) from e

        if response.status_code != HTTPStatus.OK:
            reason = response_dict.get('reason') or response.text
            msg = (
                f'{error_prefix} responded with error status code: {response.status_code} '
                f'and text: {reason}.'
            )
            raise RemoteError(API_KEY_ERROR_CODE_ACTION.get(response_dict.get('code'), msg))

        return response_dict

    @overload
    def _api_query_paginated(
            self,
            endpoint: Literal['v1/client/hist_trades'],
            options: dict[str, Any],
            deserialization_method: Callable[[dict[str, Any]], Any],
            entries_key: Literal['data'],
    ) -> list[SwapEvent]:
        ...

    @overload
    def _api_query_paginated(
            self,
            endpoint: Literal['v1/asset/history'],
            options: dict[str, Any],
            deserialization_method: Callable[[dict[str, Any]], Any],
            entries_key: Literal['rows'],
    ) -> list[AssetMovement]:
        ...

    def _api_query_paginated(
            self,
            endpoint: Literal['v1/client/hist_trades', 'v1/asset/history'],
            options: dict[str, Any],
            deserialization_method: Callable[[dict[str, Any]], Any],
            entries_key: Literal['data', 'rows'],
    ) -> list[SwapEvent] | (list[AssetMovement] | list):
        """Request a Woo API endpoint paginating via an options attribute."""
        assert list(options.keys()) == sorted(options.keys())  # options need to be in alphabetic order as stated in their api: https://docs.woo.org/#example  # noqa: E501
        results = []

        while True:
            call_options = options.copy()
            try:
                response = self._api_query(
                    endpoint=endpoint,
                    options=call_options,
                )
            except RemoteError as e:
                log.error(
                    f'Woo {endpoint} query failed due to a remote error: {e}',
                    options=call_options,
                )
                self.msg_aggregator.add_error(f'Got remote error while querying Woo: {e}')
                return []
            try:
                entries: list[dict[str, Any]] = response[entries_key]
            except KeyError:
                msg = f'Woo {endpoint} missing key {entries_key} in response'
                self.msg_aggregator.add_error(msg)
                log.error(f'{msg}: {response}', options=call_options)
                return []
            for entry in entries:
                try:
                    results.extend(deserialization_method(entry))
                except (DeserializationError, KeyError) as e:
                    msg = f'Missing key {e}' if isinstance(e, KeyError) else str(e)
                    log.error(f'Woo {endpoint} {msg}: {entry}')
                    self.msg_aggregator.add_error(msg)
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details=f'{endpoint} query',
                    )

            if len(entries) < API_MAX_LIMIT:
                break

            try:
                options = call_options.copy()
                if endpoint == 'v1/client/hist_trades':
                    options['fromId'] = entries[-1]['id']
                else:
                    meta = response['meta']
                    if meta['current_page'] * meta['records_per_page'] < meta['total']:
                        options['page'] += 1
                    else:
                        break

            except (KeyError, TypeError) as e:
                msg = f'The entries do not have the key {e}.' if isinstance(e, KeyError) else f'The response keys have improper types {e}.'  # noqa: E501
                log.error(
                    f'Error loading all Woo {endpoint}. {msg}',
                    entries=entries,
                )
                self.msg_aggregator.add_error(
                    f'Failed to load all Woo {endpoint}. Check logs for details.',
                )
                break

        return results

    def _deserialize_asset_movement(self, movement: dict[str, Any]) -> list[AssetMovement]:
        """
        Deserialize a Woo asset movement returned from the API to AssetMovement

        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
        asset = asset_from_woo(movement['token'])
        if movement['token_side'] == 'DEPOSIT':
            address = movement['source_address']
            event_type = HistoryEventType.DEPOSIT
        else:
            address = movement['target_address']
            event_type = HistoryEventType.WITHDRAWAL
        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_floatstr(movement['created_time'])),
            asset=asset,
            amount=deserialize_fval(movement['amount']),
            fee=AssetAmount(
                asset=asset_from_woo(movement['fee_token']),
                amount=deserialize_fval_or_zero(movement['fee_amount']),
            ) if movement['fee_token'] != '' else None,
            unique_id=str(movement['id']),
            extra_data=maybe_set_transaction_extra_data(
                address=address,
                transaction_id=movement['tx_id'],
            ),
        )

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for woo
