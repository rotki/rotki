import hashlib
import hmac
import json
import logging
from collections import defaultdict
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple
from urllib.parse import urlencode

import requests
from gevent.lock import Semaphore
from requests.adapters import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_cryptocom
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
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
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
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
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
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


class CryptocomResponse(NamedTuple):
    """Response from Crypto.com API"""
    code: int
    result: Any | None = None
    message: str | None = None


class Cryptocom(ExchangeInterface):
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
            method: str,
            params: dict[str, Any],
            nonce: int,
    ) -> str:
        """Generate signature for API authentication"""
        # Sort params alphabetically
        param_str = ''
        if params:
            sorted_params = sorted(params.items())
            param_str = urlencode(sorted_params)

        sig_payload = f'{method}{self.api_key}{param_str}{nonce}'

        return hmac.new(
            self.secret,
            msg=sig_payload.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

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
                'method': method,
                'api_key': self.api_key,
                'params': params,
                'nonce': nonce,
            }

            # Add signature
            signature = self._generate_signature(
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

    def _deserialize_asset_movement(self, raw_result: dict[str, Any]) -> list[AssetMovement]:
        """Process an asset movement from Crypto.com and deserialize it.

        Can raise:
         - DeserializationError
         - UnknownAsset
         - UnsupportedAsset
        """
        # Check if the transaction is completed
        status = raw_result.get('status')
        if status != 'completed':
            log.debug(
                f'Skipped {self.name} asset movement. Status is not completed',
                raw_result=raw_result,
            )
            return []

        asset = asset_from_cryptocom(raw_result['currency'])
        amount = deserialize_fval(raw_result['amount'])
        fee = deserialize_fval_or_zero(raw_result.get('fee', '0'))
        timestamp = deserialize_timestamp_ms_from_intms(raw_result['update_time'])

        transaction_type = raw_result.get('transaction_type')
        if transaction_type == 'deposit':
            event_type: Literal[
                HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL,
            ] = HistoryEventType.DEPOSIT
        else:
            event_type = HistoryEventType.WITHDRAWAL

        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=TimestampMS(timestamp),
            asset=asset,
            amount=amount,
            fee=AssetAmount(asset=asset, amount=fee),
            unique_id=str(raw_result['id']),
            extra_data=maybe_set_transaction_extra_data(
                address=raw_result.get('address'),
                transaction_id=raw_result.get('txid'),
                extra_data=AssetMovementExtraData({'reference': str(raw_result['id'])}),
            ),
        )

    def _deserialize_trade(self, raw_result: dict[str, Any]) -> list[SwapEvent]:
        """Process a trade result from Crypto.com and deserialize it into SwapEvents.

        Can raise:
         - DeserializationError
         - UnknownAsset
         - UnsupportedAsset
        """
        # Parse the trading pair (e.g., "BTC_USDT")
        pair = raw_result['instrument_name']
        base_asset_str, quote_asset_str = pair.split('_')

        base_asset = asset_from_cryptocom(base_asset_str)
        quote_asset = asset_from_cryptocom(quote_asset_str)

        is_buy = raw_result['side'] == 'BUY'
        amount = deserialize_fval(raw_result['traded_quantity'])
        rate = deserialize_fval(raw_result['traded_price'])
        fee = deserialize_fval_or_zero(raw_result.get('fee', '0'))
        fee_currency = raw_result.get('fee_currency', '')

        spend, receive = get_swap_spend_receive(
            is_buy=is_buy,
            base_asset=base_asset,
            quote_asset=quote_asset,
            amount=amount,
            rate=Price(rate),
        )

        fee_asset = asset_from_cryptocom(fee_currency) if fee_currency else quote_asset

        return create_swap_events(
            timestamp=deserialize_timestamp_ms_from_intms(raw_result['create_time']),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(asset=fee_asset, amount=fee) if fee > ZERO else None,
            location_label=self.name,
            event_identifier=create_event_identifier_from_unique_id(
                location=self.location,
                unique_id=str(raw_result['trade_id']),
            ),
        )

    def first_connection(self) -> None:
        """Crypto.com doesn't require any initial setup"""
        if self.first_connection_made:
            return

        self.first_connection_made = True

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
            try:
                asset = asset_from_cryptocom(balance_entry['currency'])
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
                available = deserialize_fval(balance_entry['available'])
                order = deserialize_fval_or_zero(balance_entry.get('order', '0'))
                stake = deserialize_fval_or_zero(balance_entry.get('stake', '0'))
                amount = available + order + stake
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to deserialize asset amount due to {e!s}. Skipping balance result.',
                )
                continue

            if amount > ZERO:
                assets_balance[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )

        return dict(assets_balance), ''

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list['HistoryBaseEntry'], Timestamp]:
        """Return the Crypto.com asset movements and swap events"""
        self.first_connection()
        events: list[HistoryBaseEntry] = []

        # Query deposits
        try:
            response = self._api_query(
                'private/get-deposit-history',
                options={
                    'start_ts': start_ts * 1000,
                    'end_ts': end_ts * 1000,
                },
            )
            result = self._process_response(response)

            if result.code == API_SUCCESS_CODE and result.result is not None:
                for deposit in result.result.get('data', []):
                    try:
                        events.extend(self._deserialize_asset_movement(deposit))
                    except (DeserializationError, UnsupportedAsset, UnknownAsset) as e:
                        log.error(f'Error processing {self.name} deposit: {e!s}')
                        self.msg_aggregator.add_error(
                            f'Failed to deserialize a {self.name} deposit. '
                            f'Check logs for details.',
                        )
        except RemoteError as e:
            log.error(f'Failed to query {self.name} deposits: {e!s}')
            self.msg_aggregator.add_error(f'Failed to query {self.name} deposits: {e!s}')

        # Query withdrawals
        try:
            response = self._api_query(
                'private/get-withdrawal-history',
                options={
                    'start_ts': start_ts * 1000,
                    'end_ts': end_ts * 1000,
                },
            )
            result = self._process_response(response)

            if result.code == API_SUCCESS_CODE and result.result is not None:
                for withdrawal in result.result.get('data', []):
                    try:
                        events.extend(self._deserialize_asset_movement(withdrawal))
                    except (DeserializationError, UnsupportedAsset, UnknownAsset) as e:
                        log.error(f'Error processing {self.name} withdrawal: {e!s}')
                        self.msg_aggregator.add_error(
                            f'Failed to deserialize a {self.name} withdrawal. '
                            f'Check logs for details.',
                        )
        except RemoteError as e:
            log.error(f'Failed to query {self.name} withdrawals: {e!s}')
            self.msg_aggregator.add_error(f'Failed to query {self.name} withdrawals: {e!s}')

        # Query trades
        try:
            response = self._api_query(
                'private/get-trades',
                options={
                    'start_ts': start_ts * 1000,
                    'end_ts': end_ts * 1000,
                },
            )
            result = self._process_response(response)

            if result.code == API_SUCCESS_CODE and result.result is not None:
                for trade in result.result.get('data', []):
                    try:
                        events.extend(self._deserialize_trade(trade))
                    except (DeserializationError, UnsupportedAsset, UnknownAsset) as e:
                        log.error(f'Error processing {self.name} trade: {e!s}')
                        self.msg_aggregator.add_error(
                            f'Failed to deserialize a {self.name} trade. Check logs for details.',
                        )
        except RemoteError as e:
            log.error(f'Failed to query {self.name} trades: {e!s}')
            self.msg_aggregator.add_error(f'Failed to query {self.name} trades: {e!s}')

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
