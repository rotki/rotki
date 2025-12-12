import json
import logging
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

import requests
from gevent.lock import Semaphore
from requests.adapters import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_cryptocom
from rotkehlchen.constants import MONTH_IN_MILLISECONDS, WEEK_IN_MILLISECONDS, ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_timestamp_ms_from_intms,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    Location,
    Price,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Rate Limits
API_REQUEST_RETRY_TIMES: Final = 2
API_REQUEST_RETRY_AFTER_SECONDS: Final = 60

# API result constants
API_SUCCESS_CODE: Final = 0

DEPOSIT_WITHDRAWAL_PAGE_SIZE: Final = 200  # max allowed by api
DEPOSIT_ARRIVED_STATUS: Final = '1'
WITHDRAWAL_COMPLETED_STATUS: Final = '5'
TRADES_LIMIT: Final = 100  # max allowed by api
MAX_TRADES_AGE: Final = MONTH_IN_MILLISECONDS * 6  # only the last 6 months of trades are available

# Max recursion when sorting api parameters
MAX_PARAMS_SORT_LEVEL: Final = 3


def params_to_str(obj: dict, level: int) -> str:
    """Crypto.com API parameter sorting and serialization for signing.
    https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html?python#digital-signature
    """
    if level >= MAX_PARAMS_SORT_LEVEL:
        return str(obj)

    return_str = ''
    for key in sorted(obj):
        return_str += key
        if (obj_key := obj[key]) is None:
            return_str += 'null'
        elif isinstance(obj_key, list):
            for sub_obj in obj_key:
                return_str += params_to_str(sub_obj, level + 1)
        else:
            return_str += str(obj_key)

    return return_str


def ts_ms_to_ns(ts: TimestampMS) -> int:
    return ts * 1_000_000


class CryptocomResponse(NamedTuple):
    """Response from Crypto.com API"""
    code: int
    result: Any | None = None
    message: str | None = None


class Cryptocom(ExchangeInterface, SignatureGeneratorMixin):
    """Crypto.com exchange api docs:
    https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html
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
            location=Location.CRYPTOCOM,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = 'https://api.crypto.com/exchange/v1'
        self.nonce_lock = Semaphore()

    def _generate_signature(
            self,
            request_id: int,
            method: str,
            params: dict[str, Any],
            nonce: int,
    ) -> str:
        """Generate signature for API authentication"""
        param_str = params_to_str(params, 0) if len(params) > 0 else ''
        return self.generate_hmac_signature(
            message=f'{method}{request_id}{self.api_key}{param_str}{nonce}',
        )

    def _api_query(
            self,
            method: Literal[
                'private/user-balance',
                'private/get-trades',
                'private/get-deposit-history',
                'private/get-withdrawal-history',
            ],
            options: dict[str, Any] | None = None,
    ) -> Response:
        """Request a Crypto.com API endpoint"""
        with self.nonce_lock:
            nonce = ts_now_in_ms()
            params = options.copy() if options else {}

            # Create request body
            request_body = {
                'id': (request_id := 1),
                'method': method,
                'api_key': self.api_key,
                'params': params,
                'nonce': nonce,
            }

            # Add signature
            signature = self._generate_signature(
                request_id=request_id,
                method=method,
                params=params,
                nonce=nonce,
            )
            request_body_dict: dict[str, Any] = request_body
            request_body_dict['sig'] = signature
            request_url = f'{self.base_uri}/{method}'
            log.debug(f'{self.name} API request', request_url=request_url)
            try:
                response = self.session.post(
                    url=request_url,
                    json=request_body_dict,
                    headers={'Content-Type': 'application/json'},
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} request at {request_url} connection error: {e!s}.',
                ) from e

        return response

    def _process_response(self, response: Response) -> CryptocomResponse:
        """Process API response and handle errors"""
        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'{self.name} query responded with HTTP status '
                f'{response.status_code}: {response.text}',
            )

        try:
            data = jsonloads_dict(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
            ) from e

        code = data.get('code', -1)
        result = data.get('result')
        message = data.get('message')

        return CryptocomResponse(code=code, result=result, message=message)

    def _deserialize_asset_movement(
            self,
            raw_result: dict[str, Any],
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list[AssetMovement]:
        """Process an asset movement from Crypto.com and deserialize it.

        Can raise:
         - DeserializationError
         - UnknownAsset
         - UnsupportedAsset
         - KeyError
        """
        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=deserialize_timestamp_ms_from_intms(raw_result['create_time']),
            asset=(asset := asset_from_cryptocom(raw_result['currency'])),
            amount=deserialize_fval(raw_result['amount']),
            fee=AssetAmount(
                asset=asset,
                amount=deserialize_fval(raw_fee),
            ) if (raw_fee := raw_result.get('fee')) is not None else None,
            unique_id=str(raw_result['id']),
            extra_data=maybe_set_transaction_extra_data(
                address=raw_result.get('address'),
                # the txid field from the api sometimes contains something like `/27` at the end
                # so only take the actual hash (`0x` + 64 chars) from the beginning of the string.
                transaction_id=txid[:66] if (txid := raw_result.get('txid')) is not None else None,
                extra_data=AssetMovementExtraData({'reference': str(raw_result['id'])}),
            ),
        )

    def _deserialize_trade(self, raw_result: dict[str, Any]) -> list[SwapEvent]:
        """Process a trade result from Crypto.com and deserialize it into SwapEvents.

        Can raise:
         - DeserializationError
         - UnknownAsset
         - UnsupportedAsset
         - KeyError
        """
        # Parse the instrument name (e.g., "BTC_USDT")
        base_asset_str, quote_asset_str = raw_result['instrument_name'].split('_')
        spend, receive = get_swap_spend_receive(
            is_buy=raw_result['side'] == 'BUY',
            base_asset=asset_from_cryptocom(base_asset_str),
            quote_asset=asset_from_cryptocom(quote_asset_str),
            amount=deserialize_fval(raw_result['traded_quantity']),
            rate=Price(deserialize_fval(raw_result['traded_price'])),
        )
        return create_swap_events(
            timestamp=deserialize_timestamp_ms_from_intms(raw_result['create_time']),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=asset_from_cryptocom(raw_result['fee_instrument_name']),
                amount=deserialize_fval_force_positive(raw_fee),
            ) if (raw_fee := raw_result.get('fees')) is not None else None,
            location_label=self.name,
            group_identifier=create_group_identifier_from_unique_id(
                location=self.location,
                unique_id=str(raw_result['trade_id']),
            ),
        )

    def first_connection(self) -> None:
        """Crypto.com doesn't require any initial setup"""
        if self.first_connection_made:
            return

        self.first_connection_made = True

    def deserialize_balance(
            self,
            new_balance_data: dict[str, Any],
            balance_key: str,
            existing_balances: defaultdict['AssetWithOracles', Balance],
    ) -> defaultdict['AssetWithOracles', Balance]:
        """Deserialize a balance dict using the amount from the specified balance_key.
        Returns the updated existing_balances.
        """
        if (instrument_name := new_balance_data.get('instrument_name')) is None:
            log.error(f'Found {self.name} balance with no instrument_name. Should not happen.')
            return existing_balances

        try:
            if (amount := deserialize_fval(new_balance_data[balance_key])) > ZERO:
                asset = asset_from_cryptocom(instrument_name)
                existing_balances[asset] += Balance(
                    amount=amount,
                    value=amount * Inquirer.find_main_currency_price(asset),
                )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found unsupported {self.name} asset {e.identifier} due to: {e!s}. '
                f'Ignoring its balance query.',
            )
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='balance query',
            )
        except DeserializationError as e:
            self.msg_aggregator.add_error(
                f'Error processing {self.name} {instrument_name} balance result due to inability '
                f'to deserialize asset amount due to {e!s}. Skipping balance result.',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Error processing {self.name} {instrument_name} balance result due to inability '
                f'to query price: {e!s}. Skipping balance result.',
            )

        return existing_balances

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        """Return the account exchange balances on Crypto.com"""
        self.first_connection()

        response = self._api_query('private/user-balance')
        result = self._process_response(response)

        if result.code != API_SUCCESS_CODE:
            return None, f'{self.name} balance query failed: {result.message}'

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)

        if result.result is not None:
            balance_data = result.result.get('data', [])
        else:
            balance_data = []

        for balance_entry in balance_data:
            if len(position_balances := balance_entry['position_balances']) > 0:
                for position_entry in position_balances:
                    assets_balance = self.deserialize_balance(
                        new_balance_data=position_entry,
                        balance_key='quantity',
                        existing_balances=assets_balance,
                    )
            else:  # No positions - the account has likely not been funded yet. Get total cash balance.  # noqa: E501
                assets_balance = self.deserialize_balance(
                    new_balance_data=balance_entry,
                    balance_key='total_cash_balance',
                    existing_balances=assets_balance,
                )

        return dict(assets_balance), ''

    def _query_deposits_withdrawals(
            self,
            start_ts: TimestampMS,
            end_ts: TimestampMS,
            method: Literal['private/get-deposit-history', 'private/get-withdrawal-history'],
            query_type: Literal['deposit', 'withdrawal'],
            success_status: Literal['1', '5'],
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list['HistoryBaseEntry']:
        """Query deposits and withdrawals from the API."""
        return self._query_paginated(
            query_type=query_type,
            method=method,
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
                'page_size': DEPOSIT_WITHDRAWAL_PAGE_SIZE,
                'status': success_status,
            },
            initial_page=0,
            page_key='page',
            page_size=DEPOSIT_WITHDRAWAL_PAGE_SIZE,
            result_key=f'{query_type}_list',  # type: ignore[arg-type]  # will be a valid key
            deserialize_fn=lambda raw_result: self._deserialize_asset_movement(
                raw_result=raw_result,
                event_type=event_type,
            ),
        )

    def _query_trades(
            self,
            start_ts: TimestampMS,
            end_ts: TimestampMS,
    ) -> list['HistoryBaseEntry']:
        """Query trade history from the API.
        Note that according to the docs, this can only get the history for the last 6 months.
        https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html#introduction-3
        Also, the time window can only be a max of 1 week per request.
        https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html#private-get-trades
        """
        if (now := ts_now_in_ms()) - end_ts > MAX_TRADES_AGE:
            log.warning(f'Cannot query {self.name} trades older than 6 months.')
            return []
        elif now - start_ts > MAX_TRADES_AGE:
            from_ts = now - MAX_TRADES_AGE
        else:
            from_ts = start_ts

        to_ts = (
            from_ts + WEEK_IN_MILLISECONDS
            if end_ts - from_ts > WEEK_IN_MILLISECONDS
            else end_ts
        )
        events: list[HistoryBaseEntry] = []
        while True:
            events.extend(self._query_paginated(
                query_type='trade',
                method='private/get-trades',
                options={'start_time': ts_ms_to_ns(TimestampMS(from_ts)), 'limit': TRADES_LIMIT},
                initial_page=ts_ms_to_ns(TimestampMS(to_ts)),
                page_key='end_time',
                page_size=TRADES_LIMIT,
                result_key='data',
                deserialize_fn=self._deserialize_trade,
            ))
            if to_ts >= end_ts:
                log.debug(f'Finished querying {self.name} trades from {start_ts} to {end_ts}')
                break

            from_ts = to_ts
            to_ts = min(to_ts + WEEK_IN_MILLISECONDS, end_ts)

        return events

    def _query_paginated(
            self,
            query_type: Literal['deposit', 'withdrawal', 'trade'],
            method: Literal['private/get-trades', 'private/get-deposit-history', 'private/get-withdrawal-history'],  # noqa: E501
            options: dict[str, Any],
            initial_page: int | TimestampMS,
            page_key: Literal['page', 'end_time'],
            page_size: int,
            result_key: Literal['data', 'deposit_list', 'withdrawal_list'],
            deserialize_fn: 'Callable[[dict[str, Any]], list[AssetMovement]] | Callable[[dict[str, Any]], list[SwapEvent]]',  # noqa: E501
    ) -> list['HistoryBaseEntry']:
        """Query the paginated deposits, withdrawals, or trades from the API.
        https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html#private-get-deposit-history
        https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html#private-get-withdrawal-history
        https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html#private-get-trades
        """
        options[page_key] = initial_page
        events: list[HistoryBaseEntry] = []
        while True:
            try:
                result = self._process_response(self._api_query(method=method, options=options))
                if result.code != API_SUCCESS_CODE or result.result is None:
                    log.error(f'Failed to query {self.name} {query_type}s: {result.message}')
                    break

                for raw_asset_movement in (raw_list := result.result.get(result_key, [])):
                    try:
                        events.extend(deserialize_fn(raw_asset_movement))
                    except (DeserializationError, UnsupportedAsset, UnknownAsset, KeyError) as e:
                        msg = f'missing key: {e!s}' if isinstance(e, KeyError) else str(e)
                        log.error(
                            f'Error processing {self.name} {query_type}: '
                            f'{raw_asset_movement} due to {msg}',
                        )
                        self.msg_aggregator.add_error(
                            f'Failed to deserialize a {self.name} {query_type}. '
                            f'Check the logs for details.',
                        )

                if len(raw_list) < page_size:
                    break

                if page_key == 'page':
                    options[page_key] += 1
                else:  # trades endpoint pages by timestamp
                    options[page_key] = raw_list[-1]['create_time_ns']
            except RemoteError as e:
                self.msg_aggregator.add_error(f'Failed to query {self.name} {query_type}s: {e!s}')
                break

        return events

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple[list['HistoryBaseEntry'], Timestamp]:
        """Return the Crypto.com asset movements and swap events"""
        self.first_connection()
        events = self._query_deposits_withdrawals(
            start_ts=(start_ts_ms := ts_sec_to_ms(start_ts)),
            end_ts=(end_ts_ms := ts_sec_to_ms(end_ts)),
            query_type='deposit',
            method='private/get-deposit-history',
            success_status=DEPOSIT_ARRIVED_STATUS,
            event_type=HistoryEventType.DEPOSIT,
        )
        events.extend(self._query_deposits_withdrawals(
            start_ts=start_ts_ms,
            end_ts=end_ts_ms,
            query_type='withdrawal',
            method='private/get-withdrawal-history',
            success_status=WITHDRAWAL_COMPLETED_STATUS,
            event_type=HistoryEventType.WITHDRAWAL,
        ))
        events.extend(self._query_trades(start_ts=start_ts_ms, end_ts=end_ts_ms))
        return events, end_ts

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Crypto.com API key is good for usage in rotki"""
        try:
            response = self._api_query('private/user-balance')
            result = self._process_response(response)

            if result.code != API_SUCCESS_CODE:
                return False, f'Crypto.com API key validation failed: {result.message}'
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # Crypto.com margin trading not implemented yet
