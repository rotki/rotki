import hashlib
import json
import logging
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode

import requests
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bit2me
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
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
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now_in_ms, ts_sec_to_ms

# cache_response_timewise not needed per review; remove usage
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# API Error codes and messages
API_KEY_ERROR_MESSAGE: Final = (
    'Provided API key/secret is invalid or does not have enough permissions.'
)

# Rate Limits and retry
API_REQUEST_RETRY_TIMES: Final = 2
API_REQUEST_RETRY_AFTER_SECONDS: Final = 60

# Max limits for API endpoints
API_TRADES_MAX_LIMIT: Final = 100
API_MOVEMENTS_MAX_LIMIT: Final = 100
API_ORDERS_MAX_LIMIT: Final = 100
API_TRANSACTIONS_MAX_LIMIT: Final = 100


class Bit2me(ExchangeInterface, SignatureGeneratorMixin):
    """Bit2me exchange API implementation.

    API Documentation: https://bit2me.com/api-docs (update with actual URL)
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
            location=Location.BIT2ME,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        # API gateway for trading spot - see https://github.com/bit2me-devs/trading-spot-samples
        self.base_uri = 'https://gateway.bit2me.com'
        self.session.headers.update(
            {
                'Content-type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'rotki',
            },
        )
        self.nonce_lock = Semaphore()

    # edit_exchange_credentials override is unnecessary; rely on base implementation

    def first_connection(self) -> None:
        """No-op first connection hook for Bit2Me.

        Bit2Me does not require prefetching markets or metadata before use.
        """
        if not self.first_connection_made:
            self.first_connection_made = True

    def validate_api_key(self) -> tuple[bool, str]:
        """Validate Bit2Me API credentials by hitting a minimal private endpoint.

        Uses the balances endpoint which requires valid API key/secret and permissions.
        """
        try:
            # Any auth failure will raise RemoteError via _process_error_response
            self._api_query('balances')
        except RemoteError as e:
            # Return backend-friendly message for the UI
            return False, str(e)

        return True, ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> list[MarginPosition]:
        """Bit2Me does not provide margin positions; return empty list."""
        return []

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,  # pylint: disable=unused-argument
    ) -> tuple['Sequence[HistoryBaseEntry]', Timestamp]:
        """Query all history events from Bit2me.

        This method combines trade history, asset movements (deposits/withdrawals),
        brokerage transactions (purchases/sales), EARN (staking) movements,
        and airdrops into a single list of history events.
        """
        events: list[HistoryBaseEntry] = []

        # Get deposits/withdrawals from /v2/wallet/transaction
        movements = self.query_online_deposits_withdrawals(start_ts, end_ts)
        events.extend(movements)

        # Get brokerage trades from /v2/wallet/transaction (type=transfer, subtype=purchase)
        brokerage_trades = self._query_brokerage_trades(start_ts, end_ts)
        events.extend(brokerage_trades)

        # Get EARN (staking) movements from /v2/wallet/transaction (subtype=earn)
        earn_movements = self._query_earn_movements(start_ts, end_ts)
        events.extend(earn_movements)

        # Get airdrops from /v2/wallet/transaction (type=transfer, subtype=social-pay)
        airdrops = self._query_airdrops(start_ts, end_ts)
        events.extend(airdrops)

        # Get exchange trades from /v1/trading/trade
        trades, _ = self.query_online_trade_history(start_ts, end_ts)
        events.extend(trades)

        return events, end_ts

    @protect_with_lock()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query Bit2me balances for all assets."""
        try:
            response = self._api_query('balances')
        except RemoteError as e:
            msg = f'Bit2me API request failed. {e!s}'
            log.error(msg)
            return None, msg

        try:
            response_data = jsonloads_list(response.text)
        except JSONDecodeError as e:
            msg = f'Bit2me returned invalid JSON response. {e!s}'
            log.error(msg)
            return None, msg

        # Bit2me API returns a list of balances
        # Each item has: currency, balance, blockedBalance, blockedOutputBalance
        # response_data is already validated as a list by jsonloads_list

        assets_balance: dict[AssetWithOracles, Balance] = {}

        for balance_entry in response_data:
            try:
                # Get asset symbol (API field is 'currency')
                asset_symbol = balance_entry.get('currency')
                if not asset_symbol:
                    log.warning(f'Bit2me balance entry missing currency symbol: {balance_entry}')
                    continue

                # Calculate total balance (available + blocked amounts)
                balance_amount = deserialize_fval(
                    balance_entry.get('balance', '0'),
                    'balance',
                    'bit2me',
                )
                blocked_balance = deserialize_fval(
                    balance_entry.get('blockedBalance', '0'),
                    'blockedBalance',
                    'bit2me',
                )
                blocked_output_balance = deserialize_fval(
                    balance_entry.get('blockedOutputBalance', '0'),
                    'blockedOutputBalance',
                    'bit2me',
                )

                total_amount = balance_amount + blocked_balance + blocked_output_balance

                # Skip zero balances
                if total_amount == ZERO:
                    continue

                # Convert asset symbol to rotki asset
                try:
                    asset = asset_from_bit2me(asset_symbol)
                except (UnknownAsset, UnsupportedAsset) as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported Bit2me asset {asset_symbol}. '
                        f'{e!s}. Ignoring its balance.',
                    )
                    continue

                assets_balance[asset] = Balance(amount=total_amount)

            except DeserializationError as e:
                msg = f'Error processing Bit2me balance entry {balance_entry}. {e!s}'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Failed to deserialize a Bit2me balance. {e!s}. Check logs for details.',
                )
                continue

        # Add EARN balances (staking positions)
        earn_balances = self._query_earn_balances()
        for asset, earn_balance in earn_balances.items():
            if asset in assets_balance:
                # Add to existing balance
                assets_balance[asset] = Balance(
                    amount=assets_balance[asset].amount + earn_balance.amount,
                )
            elif earn_balance.amount > ZERO:
                assets_balance[asset] = earn_balance

        return assets_balance, ''

    def _query_earn_balances(self) -> dict[AssetWithOracles, Balance]:
        """Calculate EARN balances by summing earn transactions.

        EARN balances are not directly queryable via API. We calculate them by:
        - withdrawal/earn (dest_class=earn) = deposit TO earn (adds to balance)
        - deposit/earn (dest_class=pocket) = withdrawal FROM earn (subtracts from balance)
        """
        # Use a dict to accumulate amounts by currency symbol
        earn_amounts: dict = {}  # currency -> FVal amount

        try:
            options = {'limit': API_TRANSACTIONS_MAX_LIMIT}
            response = self._api_query('transactions', options=options)
        except RemoteError as e:
            log.warning(f'Failed to query Bit2me transactions for EARN balances: {e!s}')
            return {}

        try:
            response_data = jsonloads_dict(response.text)
        except JSONDecodeError:
            log.warning('Bit2me returned invalid JSON for EARN balance query')
            return {}

        transactions = response_data.get('data', [])

        for tx in transactions:
            try:
                subtype = tx.get('subtype', '')
                if subtype != 'earn':
                    continue

                tx_type = tx.get('type', '')
                destination = tx.get('destination', {})
                origin = tx.get('origin', {})
                dest_class = destination.get('class', '')

                # Determine if this is a deposit TO earn or withdrawal FROM earn
                if tx_type == 'withdrawal' and dest_class == 'earn':
                    # Money going INTO earn (we consider origin amount and currency)
                    amount_str = origin.get('amount', '0')
                    currency = origin.get('currency', '')
                    amount = deserialize_fval(amount_str, 'earn_amount', 'bit2me')
                elif tx_type == 'deposit' and dest_class == 'pocket':
                    # Money coming OUT of earn (negative)
                    amount_str = destination.get('amount', '0')
                    currency = destination.get('currency', '')
                    amount = -deserialize_fval(amount_str, 'earn_amount', 'bit2me')
                else:
                    continue

                if not currency:
                    continue

                if currency not in earn_amounts:
                    earn_amounts[currency] = ZERO
                earn_amounts[currency] += amount

            except (KeyError, DeserializationError) as e:
                log.debug(f'Skipping earn transaction due to error: {e!s}')
                continue

        # Convert to Balance objects, only include positive balances
        result: dict[AssetWithOracles, Balance] = {}
        for currency, amount in earn_amounts.items():
            if amount > ZERO:
                try:
                    asset = asset_from_bit2me(currency)
                    result[asset] = Balance(amount=amount)
                except (UnknownAsset, UnsupportedAsset):
                    continue

        return result

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[SwapEvent], tuple[Timestamp, Timestamp]]:
        """Query Bit2me trade history within a time range."""
        log.debug(
            f'Querying {self.name} trade history',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        trades: list[SwapEvent] = []

        # Query trades with pagination
        # Bit2me API: GET /v1/trading/trade?limit=100
        options = {'limit': API_TRADES_MAX_LIMIT}

        try:
            response = self._api_query('trades', options=options)
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query {self.name} trade history. {e!s}',
            )
            return trades, (start_ts, end_ts)

        try:
            response_data = jsonloads_dict(response.text)
            # Extract trades array from response wrapper
            trades_list = response_data.get('trades', [])
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON for trades. {e!s}'
            log.error(msg)
            self.msg_aggregator.add_error(msg)
            return trades, (start_ts, end_ts)

        # Process each trade
        for raw_trade in trades_list:
            try:
                # Deserialize the trade
                trade_events = self._deserialize_trade(raw_trade)

                # Filter by time range (check first event's timestamp)
                if trade_events:
                    trade_timestamp = ts_ms_to_sec(trade_events[0].timestamp)
                    if trade_timestamp < start_ts or trade_timestamp > end_ts:
                        continue

                    trades.extend(trade_events)

            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                msg = f'Failed to deserialize {self.name} trade. {e!s}'
                log.error(msg, raw_trade=raw_trade)
                self.msg_aggregator.add_error(
                    f'Failed to process a {self.name} trade. Check logs for details.',
                )
                continue

        return trades, (start_ts, end_ts)

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query Bit2me deposits and withdrawals within a time range.

        Uses the /v2/wallet/transaction endpoint which returns transactions with:
        - type: 'deposit', 'withdraw', etc.
        - origin/destination: pocketId, amount, currency, address
        """
        log.debug(
            f'Querying {self.name} deposits/withdrawals',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        movements: list[AssetMovement] = []

        # Query transactions with pagination
        # Bit2me API: GET /v2/wallet/transaction?limit=100
        options = {'limit': API_TRANSACTIONS_MAX_LIMIT}

        try:
            response = self._api_query('transactions', options=options)
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query {self.name} transactions. {e!s}',
            )
            return movements

        try:
            response_data: dict[str, Any] | list[Any] = json.loads(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON for transactions. {e!s}'
            log.error(msg)
            self.msg_aggregator.add_error(msg)
            return movements

        # Bit2me transactions can come as {'data': [...]} or directly as a list
        if isinstance(response_data, dict) and 'data' in response_data:
            transactions_list = response_data['data']
        elif isinstance(response_data, list):
            transactions_list = response_data
        else:
            log.error(f'Unexpected Bit2me transactions response format: {response_data}')
            return movements

        # Process each transaction
        for raw_transaction in transactions_list:
            try:
                # Deserialize the transaction (returns list of events or None)
                movement_events = self._deserialize_asset_movement(raw_transaction)

                # Skip if deserializer returned None (e.g., internal transfers)
                if movement_events is None:
                    continue

                # Filter by time range (check first event's timestamp)
                if movement_events:
                    timestamp = ts_ms_to_sec(movement_events[0].timestamp)
                    if timestamp < start_ts or timestamp > end_ts:
                        continue

                movements.extend(movement_events)

            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                msg = f'Failed to deserialize {self.name} transaction. {e!s}'
                log.error(msg, raw_transaction=raw_transaction)
                self.msg_aggregator.add_error(
                    f'Failed to process a {self.name} transaction. Check logs for details.',
                )
                continue

        return movements

    def _query_brokerage_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Query Bit2me brokerage trades (purchases/sales) within a time range.

        These are transactions with type="transfer" and subtype="purchase".
        They represent direct crypto purchases with EUR or crypto-to-crypto swaps
        through Bit2Me's brokerage service.

        Uses the same /v2/wallet/transaction endpoint as deposits/withdrawals.
        """
        log.debug(
            f'Querying {self.name} brokerage trades',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        brokerage_trades: list[SwapEvent] = []

        options = {'limit': API_TRANSACTIONS_MAX_LIMIT}

        try:
            response = self._api_query('transactions', options=options)
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query {self.name} brokerage transactions. {e!s}',
            )
            return brokerage_trades

        try:
            response_data: dict[str, Any] | list[Any] = json.loads(response.text)
        except JSONDecodeError as e:
            msg = f'{self.name} returned invalid JSON for brokerage transactions. {e!s}'
            log.error(msg)
            self.msg_aggregator.add_error(msg)
            return brokerage_trades

        # Extract transactions list
        if isinstance(response_data, dict) and 'data' in response_data:
            transactions_list = response_data['data']
        elif isinstance(response_data, list):
            transactions_list = response_data
        else:
            log.error(f'Unexpected Bit2me transactions response format: {response_data}')
            return brokerage_trades

        # Process each transaction looking for brokerage purchases
        for raw_transaction in transactions_list:
            try:
                transaction_type = raw_transaction.get('type', '')
                subtype = raw_transaction.get('subtype', '')

                # Only process brokerage purchases (type=transfer, subtype=purchase)
                if transaction_type != 'transfer' or subtype != 'purchase':
                    continue

                # Deserialize the brokerage trade
                trade_events = self._deserialize_brokerage_trade(raw_transaction)

                # Filter by time range
                if trade_events:
                    timestamp = ts_ms_to_sec(trade_events[0].timestamp)
                    if timestamp < start_ts or timestamp > end_ts:
                        continue

                brokerage_trades.extend(trade_events)

            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                msg = f'Failed to deserialize {self.name} brokerage trade. {e!s}'
                log.error(msg, raw_transaction=raw_transaction)
                self.msg_aggregator.add_error(
                    f'Failed to process a {self.name} brokerage trade. Check logs for details.',
                )
                continue

        log.debug(f'Found {len(brokerage_trades)} brokerage trades from {self.name}')
        return brokerage_trades

    def _generate_signature(
            self,
            path: str,
            body: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Generate authentication signature for Bit2me API.

        Following the official Node.js sample implementation:
        - nonce = current time in ms
        - message = "nonce:path" or "nonce:path:json_body" (no spaces in JSON)
        - signature = base64(hmac_sha512(secret, sha256(message)))

        Args:
            path: API path including query parameters
            body: Optional request body

        Returns:
            Tuple of (nonce, signature)
        """
        import base64

        nonce = str(ts_now_in_ms())

        if body is not None and len(body) > 0:
            # Use compact JSON (no spaces) as in official sample
            body_json = json.dumps(body, separators=(',', ':'))
            message = f'{nonce}:{path}:{body_json}'
        else:
            message = f'{nonce}:{path}'

        # First SHA256, then HMAC-SHA512
        sha256_digest = hashlib.sha256(message.encode()).digest()
        hmac_digest = self.generate_hmac_signature(
            sha256_digest,
            digest_algorithm=hashlib.sha512,
        )
        signature = base64.b64encode(bytes.fromhex(hmac_digest)).decode()

        return nonce, signature

    def _api_query(
            self,
            endpoint: Literal[
            'balances',
            'trades',
            'orders',
            'transactions',
        ],
            options: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Request a Bit2me API endpoint.

        Args:
            endpoint: The API endpoint to query
            options: Optional query parameters

        Returns:
            The API response

        Raises:
            RemoteError: If the request fails
        """
        call_options = options.copy() if options else {}

        # Define endpoint paths according to Bit2me API
        if endpoint == 'balances':
            method = 'get'
            api_path = '/v1/wallet/pocket'
            request_url = f'{self.base_uri}{api_path}'
        elif endpoint == 'trades':
            method = 'get'
            api_path = '/v1/trading/trade'
            if call_options:
                request_url = f'{self.base_uri}{api_path}?{urlencode(call_options)}'
            else:
                request_url = f'{self.base_uri}{api_path}'
        elif endpoint == 'orders':
            method = 'get'
            api_path = '/v1/trading/order'
            if call_options:
                request_url = f'{self.base_uri}{api_path}?{urlencode(call_options)}'
            else:
                request_url = f'{self.base_uri}{api_path}'
        elif endpoint == 'transactions':
            method = 'get'
            api_path = '/v2/wallet/transaction'
            if call_options:
                request_url = f'{self.base_uri}{api_path}?{urlencode(call_options)}'
            else:
                request_url = f'{self.base_uri}{api_path}'
        else:
            raise AssertionError(f'Unexpected {self.name} endpoint type: {endpoint}')

        with self.nonce_lock:
            # Generate authentication signature
            # Extract path with query params for signature
            path_for_signature = request_url.replace(self.base_uri, '')
            nonce, signature = self._generate_signature(path_for_signature)

            # Set authentication headers per request
            auth_headers = {
                'x-api-key': self.api_key,
                'api-signature': signature,
                'x-nonce': nonce,
            }

            log.debug(f'{self.name} API request', request_url=request_url)
            try:
                response = self.session.request(
                    method=method,
                    url=request_url,
                    headers=auth_headers,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} {method} request at {request_url} connection error: {e!s}.',
                ) from e

        # Check for API errors
        if response.status_code != HTTPStatus.OK:
            self._process_error_response(response)

        return response

    def _process_error_response(self, response: requests.Response) -> None:
        """Process an error response from the API.

        Raises:
            RemoteError: Always raises with appropriate error message
        """
        try:
            error_data = jsonloads_dict(response.text)
            error_message = error_data.get('message', response.text)
        except JSONDecodeError:
            error_message = response.text

        log.error(
            f'{self.name} API error',
            status_code=response.status_code,
            error=error_message,
        )

        raise RemoteError(
            f'{self.name} API error: {error_message}',
        )

    def _deserialize_trade(self, raw_trade: dict[str, Any]) -> list[SwapEvent]:
        """Deserialize a trade from Bit2me API response.

        Expected structure (to be confirmed with real data):
        {
            "id": "trade_id",
            "timestamp": 1234567890000,
            "symbol": "BTC-EUR",
            "side": "buy" or "sell",
            "price": "50000.00",
            "amount": "0.01",
            "fee": "0.5",
            "feeAsset": "EUR"
        }

        Args:
            raw_trade: Raw trade data from API

        Returns:
            List of SwapEvent(s) representing the trade

        Raises:
            DeserializationError: If deserialization fails
            UnknownAsset: If asset cannot be resolved
            UnsupportedAsset: If asset is not supported
        """
        try:
            # Extract trade ID
            trade_id = str(raw_trade['id'])

            # Parse timestamp
            timestamp_ms = deserialize_timestamp_ms_from_intms(raw_trade['timestamp'])

            # Parse trading pair (e.g., "BTC-EUR")
            symbol = raw_trade['symbol']
            if '-' not in symbol:
                raise DeserializationError(
                    f'Invalid Bit2me trading pair format: {symbol}. Expected format: BASE-QUOTE',
                )
            base_symbol, quote_symbol = symbol.split('-', 1)

            # Resolve assets
            base_asset = asset_from_bit2me(base_symbol)
            quote_asset = asset_from_bit2me(quote_symbol)

            # Parse amounts and price
            amount = deserialize_fval(raw_trade['amount'])
            price = deserialize_price(raw_trade['price'])
            side = raw_trade['side']

            # Determine spend/receive based on side
            is_buy = side.lower() == 'buy'
            spend, receive = get_swap_spend_receive(
                is_buy=is_buy,
                base_asset=base_asset,
                quote_asset=quote_asset,
                amount=amount,
                rate=price,
            )

            # Parse fee
            fee_amount = deserialize_fval_or_zero(raw_trade.get('fee', '0'))
            fee_asset_symbol = raw_trade.get('feeAsset', quote_symbol)
            fee_asset = asset_from_bit2me(fee_asset_symbol)

            # Create swap events
            return create_swap_events(
                spend=spend,
                receive=receive,
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                fee=AssetAmount(asset=fee_asset, amount=fee_amount),
                group_identifier=create_group_identifier_from_unique_id(self.location, trade_id),
            )

        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me trade: {e}. Raw trade: {raw_trade}',
            ) from e

    def _store_historical_price(
            self,
            from_asset: AssetWithOracles,
            to_asset: AssetWithOracles,
            price: 'FVal',
            timestamp: Timestamp,
    ) -> None:
        """Store a historical price from Bit2Me in the global database.

        This allows rotki to use the actual exchange rate from the transaction
        instead of relying on price oracles. Manual prices have priority over
        oracle prices in rotki's price lookup.

        Args:
            from_asset: The base asset (e.g., BTC)
            to_asset: The quote asset (e.g., EUR)
            price: The exchange rate (e.g., 89831.698 for BTC/EUR)
            timestamp: The timestamp of the transaction
        """
        try:
            historical_price = HistoricalPrice(
                from_asset=from_asset,
                to_asset=to_asset,
                source=HistoricalPriceOracle.MANUAL,
                timestamp=timestamp,
                price=Price(price),
            )
            GlobalDBHandler.add_single_historical_price(historical_price)
            log.debug(
                f'Stored Bit2Me historical price: {from_asset} -> {to_asset} = {price} '
                f'at {timestamp}',
            )
        except Exception as e:  # pylint: disable=broad-except
            log.warning(
                f'Failed to store Bit2Me historical price: {e}. '
                f'Price oracle will be used instead.',
            )

    def _deserialize_earn_movement(
            self,
            raw_movement: dict[str, Any],
    ) -> HistoryEvent | None:
        """Deserialize an EARN (staking) movement from Bit2Me API response.

        EARN movements are internal transfers between pocket and earn program.
        The API naming is confusing:
        - type="withdrawal" with destination.class="earn" → DEPOSIT to EARN
        - type="deposit" with origin.class="earn" → WITHDRAWAL from EARN

        We use origin.class and destination.class to determine the actual direction.

        Args:
            raw_movement: Raw movement data from API

        Returns:
            HistoryEvent for the staking operation or None if not an EARN movement
        """
        try:
            subtype = raw_movement.get('subtype', '')
            if subtype != 'earn':
                return None

            # Get origin and destination info
            origin = raw_movement.get('origin', {})
            destination = raw_movement.get('destination', {})
            origin_class = origin.get('class', '')
            dest_class = destination.get('class', '')

            # Determine direction based on class, not type
            # destination.class == "earn" means money goes INTO earn → DEPOSIT_ASSET
            # origin.class == "earn" means money comes FROM earn → REMOVE_ASSET
            if dest_class == 'earn':
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                asset_symbol = origin.get('currency', destination.get('currency', ''))
                amount = deserialize_fval(
                    origin.get('amount', destination.get('amount', '0')),
                )
                notes = f'Deposit to Bit2Me Earn: {amount} {asset_symbol}'
            elif origin_class == 'earn':
                event_subtype = HistoryEventSubType.REMOVE_ASSET
                asset_symbol = destination.get('currency', origin.get('currency', ''))
                amount = deserialize_fval(
                    destination.get('amount', origin.get('amount', '0')),
                )
                notes = f'Withdrawal from Bit2Me Earn: {amount} {asset_symbol}'
            else:
                # Unknown earn movement pattern
                log.warning(f'Unknown EARN movement pattern: {raw_movement}')
                return None

            # Parse timestamp from ISO format using shared utility
            timestamp_sec = deserialize_timestamp_from_date(
                raw_movement['date'], 'iso8601', 'bit2me',
            )
            timestamp_ms = TimestampMS(ts_sec_to_ms(timestamp_sec))

            # Resolve asset
            asset = asset_from_bit2me(asset_symbol)

            # Create staking event
            movement_id = raw_movement['id']

            return HistoryEvent(
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, movement_id,
                ),
                sequence_index=0,
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                asset=asset,
                amount=amount,
                event_type=HistoryEventType.STAKING,
                event_subtype=event_subtype,
                notes=notes,
                extra_data={'counterparty': 'bit2me_earn'},
            )

        except (KeyError, DeserializationError, UnknownAsset, UnsupportedAsset) as e:
            log.warning(f'Failed to deserialize EARN movement: {e}. Movement: {raw_movement}')
            return None

    def _query_earn_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Query and process EARN (staking) movements from Bit2Me.

        Returns:
            List of HistoryEvent representing staking deposits/withdrawals
        """
        log.debug(
            f'Querying {self.name} EARN movements',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        earn_events: list[HistoryEvent] = []
        options = {'limit': API_TRANSACTIONS_MAX_LIMIT}

        try:
            response = self._api_query('transactions', options=options)
        except RemoteError as e:
            log.error(f'Failed to query Bit2Me transactions for EARN: {e}')
            return earn_events

        try:
            response_data: dict[str, Any] | list[Any] = json.loads(response.text)
        except JSONDecodeError as e:
            log.error(f'{self.name} returned invalid JSON for EARN transactions: {e}')
            return earn_events

        # Extract transactions list
        if isinstance(response_data, dict) and 'data' in response_data:
            transactions_list = response_data['data']
        elif isinstance(response_data, list):
            transactions_list = response_data
        else:
            log.error(f'Unexpected Bit2me transactions response format: {response_data}')
            return earn_events

        for raw_transaction in transactions_list:
            try:
                subtype = raw_transaction.get('subtype', '')
                if subtype != 'earn':
                    continue

                status = raw_transaction.get('status', '')
                if status != 'completed':
                    continue

                earn_event = self._deserialize_earn_movement(raw_transaction)
                if earn_event is None:
                    continue

                # Filter by time range
                timestamp = ts_ms_to_sec(earn_event.timestamp)
                if timestamp < start_ts or timestamp > end_ts:
                    continue

                earn_events.append(earn_event)

            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                log.warning(f'Failed to process EARN transaction: {e}')
                continue

        log.debug(f'Found {len(earn_events)} EARN movements from {self.name}')
        return earn_events

    def _deserialize_airdrop(
            self,
            raw_transaction: dict[str, Any],
    ) -> HistoryEvent | None:
        """Deserialize an airdrop/gift (social-pay) from Bit2Me API response.

        Social-pay transactions are gifts/airdrops sent via email from Bit2Me.
        They have type="transfer", subtype="social-pay", and origin.class="email".

        Args:
            raw_transaction: Raw transaction data from API

        Returns:
            HistoryEvent for the airdrop or None if not valid
        """
        try:
            subtype = raw_transaction.get('subtype', '')
            if subtype != 'social-pay':
                return None

            # Get destination info (where the airdrop lands)
            destination = raw_transaction.get('destination', {})
            origin = raw_transaction.get('origin', {})

            # Get amount and currency from destination
            asset_symbol = destination.get('currency', origin.get('currency', ''))
            amount = deserialize_fval(
                destination.get('amount', origin.get('amount', '0')),
            )

            if amount <= ZERO:
                return None

            # Parse timestamp from ISO format using shared utility
            timestamp_sec = deserialize_timestamp_from_date(
                raw_transaction['date'], 'iso8601', 'bit2me',
            )
            timestamp_ms = TimestampMS(ts_sec_to_ms(timestamp_sec))

            # Resolve asset
            asset = asset_from_bit2me(asset_symbol)

            # Store historical price if available in denomination.rate
            # This allows rotki to use the actual exchange rate instead of oracles
            denomination = raw_transaction.get('denomination', {})
            denom_rate = denomination.get('rate', {})
            if denom_rate and denom_rate.get('value'):
                rate_value = deserialize_fval(denom_rate['value'])
                if rate_value > ZERO:
                    # Get the quote asset (e.g., EUR from BTC/EUR)
                    pair = denom_rate.get('pair', {})
                    quote_symbol = pair.get('quote', '')
                    if quote_symbol:
                        try:
                            quote_asset = asset_from_bit2me(quote_symbol)
                            self._store_historical_price(
                                from_asset=asset,
                                to_asset=quote_asset,
                                price=rate_value,
                                timestamp=ts_ms_to_sec(timestamp_ms),
                            )
                        except (UnknownAsset, UnsupportedAsset) as e:
                            log.debug(f'Could not store airdrop price, unknown quote asset: {e}')

            # Get sender info for notes
            sender = origin.get('fullName', 'Bit2Me')
            method = raw_transaction.get('method', 'email')

            # Create airdrop event
            transaction_id = raw_transaction['id']
            notes = f'Airdrop from {sender}: {amount} {asset_symbol} via {method}'

            return HistoryEvent(
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, transaction_id,
                ),
                sequence_index=0,
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                asset=asset,
                amount=amount,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                notes=notes,
                extra_data={'counterparty': 'bit2me'},
            )

        except (KeyError, DeserializationError, UnknownAsset, UnsupportedAsset) as e:
            log.warning(f'Failed to deserialize airdrop: {e}. Transaction: {raw_transaction}')
            return None

    def _query_airdrops(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Query and process airdrops/gifts (social-pay) from Bit2Me.

        Returns:
            List of HistoryEvent representing airdrops received
        """
        log.debug(
            f'Querying {self.name} airdrops',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        airdrop_events: list[HistoryEvent] = []
        options = {'limit': API_TRANSACTIONS_MAX_LIMIT}

        try:
            response = self._api_query('transactions', options=options)
        except RemoteError as e:
            log.error(f'Failed to query Bit2Me transactions for airdrops: {e}')
            return airdrop_events

        try:
            response_data: dict[str, Any] | list[Any] = json.loads(response.text)
        except JSONDecodeError as e:
            log.error(f'{self.name} returned invalid JSON for airdrops: {e}')
            return airdrop_events

        # Extract transactions list
        if isinstance(response_data, dict) and 'data' in response_data:
            transactions_list = response_data['data']
        elif isinstance(response_data, list):
            transactions_list = response_data
        else:
            log.error(f'Unexpected Bit2me transactions response format: {response_data}')
            return airdrop_events

        for raw_transaction in transactions_list:
            try:
                transaction_type = raw_transaction.get('type', '')
                subtype = raw_transaction.get('subtype', '')
                if transaction_type != 'transfer' or subtype != 'social-pay':
                    continue

                status = raw_transaction.get('status', '')
                if status != 'completed':
                    continue

                airdrop_event = self._deserialize_airdrop(raw_transaction)
                if airdrop_event is None:
                    continue

                # Filter by time range
                timestamp = ts_ms_to_sec(airdrop_event.timestamp)
                if timestamp < start_ts or timestamp > end_ts:
                    continue

                airdrop_events.append(airdrop_event)

            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                log.warning(f'Failed to process airdrop transaction: {e}')
                continue

        log.debug(f'Found {len(airdrop_events)} airdrops from {self.name}')
        return airdrop_events

    def _deserialize_brokerage_trade(
            self,
            raw_transaction: dict[str, Any],
    ) -> list[SwapEvent]:
        """Deserialize a brokerage purchase/sale from Bit2me transaction API.

        Brokerage transactions have type="transfer" and subtype="purchase".
        They represent direct crypto purchases with fiat or crypto-to-crypto swaps.

        The fee is calculated as the difference between what was spent and
        the value of what was received at the given exchange rate.

        Expected structure:
        {
            "id": "transaction_id",
            "date": "2025-11-18T23:33:51.381Z",
            "type": "transfer",
            "subtype": "purchase",
            "origin": {
                "amount": "100.00000000",
                "currency": "EUR"
            },
            "destination": {
                "amount": "0.00122130",
                "currency": "BTC",
                "rate": {
                    "value": "89831.698",
                    "pair": {"base": "BTC", "quote": "EUR"}
                }
            }
        }

        Args:
            raw_transaction: Raw transaction data from API

        Returns:
            List of SwapEvent(s) representing the trade

        Raises:
            DeserializationError: If deserialization fails
            UnknownAsset: If asset cannot be resolved
            UnsupportedAsset: If asset is not supported
        """
        try:
            # Extract transaction ID
            trade_id = str(raw_transaction['id'])

            # Parse timestamp from ISO format using shared utility
            timestamp_sec = deserialize_timestamp_from_date(
                raw_transaction['date'], 'iso8601', 'bit2me',
            )
            timestamp_ms = TimestampMS(ts_sec_to_ms(timestamp_sec))

            # Extract origin (what was spent) and destination (what was received)
            origin = raw_transaction['origin']
            destination = raw_transaction['destination']

            spend_amount = deserialize_fval(origin['amount'])
            spend_asset = asset_from_bit2me(origin['currency'])
            receive_amount = deserialize_fval(destination['amount'])
            receive_asset = asset_from_bit2me(destination['currency'])

            # Calculate fee from the exchange rate if available.
            # The fee is: spend_amount - (receive_amount * rate)
            # Example: 101 EUR - (0.00111364 BTC * 89831.698 EUR/BTC) = 0.9595 EUR
            fee: AssetAmount | None = None
            dest_rate = destination.get('rate', {})
            if dest_rate and dest_rate.get('value'):
                rate_value = deserialize_fval(dest_rate['value'])
                if rate_value > ZERO:
                    # Calculate the value of received amount in spend currency
                    received_value_in_spend_currency = receive_amount * rate_value
                    fee_amount = spend_amount - received_value_in_spend_currency
                    if fee_amount > ZERO:
                        fee = AssetAmount(asset=spend_asset, amount=fee_amount)

                    # Store the historical price from Bit2Me as a manual price.
                    # This allows rotki to use the actual exchange rate instead of oracles.
                    # Rate is base/quote (e.g., BTC/EUR=89831.698 means 1 BTC = 89831.698 EUR)
                    self._store_historical_price(
                        from_asset=receive_asset,
                        to_asset=spend_asset,
                        price=rate_value,
                        timestamp=ts_ms_to_sec(timestamp_ms),
                    )

            # Create spend/receive tuples
            spend = AssetAmount(asset=spend_asset, amount=spend_amount)
            receive = AssetAmount(asset=receive_asset, amount=receive_amount)

            return create_swap_events(
                spend=spend,
                receive=receive,
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                fee=fee,  # Fee calculated from exchange rate
                group_identifier=create_group_identifier_from_unique_id(self.location, trade_id),
            )

        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me brokerage trade: {e}. Raw transaction: {raw_transaction}',
            ) from e

    def _deserialize_asset_movement(
            self,
            raw_movement: dict[str, Any],
    ) -> list[AssetMovement] | None:
        """Deserialize an asset movement from Bit2me API response.

        Bit2me transaction types:
        - deposit: Incoming funds (blockchain, bank-transfer, pocket)
        - withdrawal: Outgoing funds (blockchain, pocket)
        - transfer: Can be internal exchange, purchases, or social-pay (airdrops)

        Transfer subtypes handled elsewhere:
        - purchase: Brokerage buy/sell (handled by _deserialize_brokerage_trade)
        - social-pay: Airdrops/gifts (handled by _deserialize_airdrop)
        - earn: Staking movements (handled by _deserialize_earn_movement)
        - Other transfers: Ignored (internal pocket-to-pocket)
        """
        try:
            # Extract transaction type and subtype
            transaction_type = raw_movement.get('type', '')
            subtype = raw_movement.get('subtype', '')

            # Handle transfer transactions based on subtype
            if transaction_type == 'transfer':
                if subtype == 'purchase':
                    # Purchase/sale transactions are handled as trades, not movements
                    return None
                elif subtype == 'social-pay':
                    # Social-pay (airdrops/gifts) are handled by _deserialize_airdrop
                    return None
                else:
                    # Skip other internal transfers (pocket to pocket within Bit2me)
                    return None

            # Skip EARN movements - they are handled by _deserialize_earn_movement
            if subtype == 'earn':
                return None

            # Determine if it's a deposit or withdrawal
            # Bit2Me v2 API has two formats: flat (origin_currency) or nested (origin.currency)
            # Try nested format first, fall back to flat
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
            if transaction_type == 'deposit':
                event_type = HistoryEventType.DEPOSIT
                # For deposits, use destination data
                if 'destination' in raw_movement and isinstance(raw_movement['destination'], dict):
                    # Nested format (newer API response)
                    destination = raw_movement['destination']
                    asset_symbol = destination['currency']
                    amount = deserialize_fval(destination['amount'])
                    address = destination.get('address')
                    origin = raw_movement.get('origin', {})
                    origin_amount = deserialize_fval(origin.get('amount', '0'))
                else:
                    # Flat format (older API response)
                    asset_symbol = raw_movement['destination_currency']
                    amount = deserialize_fval(raw_movement['destination_amount'])
                    address = raw_movement.get('destination_address')
                    origin_amount = deserialize_fval(raw_movement.get('origin_amount', '0'))
                fee_amount = abs(origin_amount - amount) if origin_amount > ZERO else ZERO
            elif transaction_type == 'withdrawal':
                event_type = HistoryEventType.WITHDRAWAL
                # For withdrawals, use destination amount as the actual withdrawn amount
                # and calculate fee as the difference between origin and destination
                if 'origin' in raw_movement and isinstance(raw_movement['origin'], dict):
                    # Nested format (newer API response)
                    origin = raw_movement['origin']
                    destination = raw_movement.get('destination', {})
                    asset_symbol = origin['currency']
                    origin_amount = deserialize_fval(origin['amount'])
                    destination_amount = deserialize_fval(destination.get('amount', '0'))
                    address = destination.get('address')
                else:
                    # Flat format (older API response)
                    asset_symbol = raw_movement['origin_currency']
                    origin_amount = deserialize_fval(raw_movement['origin_amount'])
                    destination_amount = deserialize_fval(
                        raw_movement.get('destination_amount', '0'),
                    )
                    address = raw_movement.get('destination_address')
                # amount is what actually arrives at destination, fee is the difference
                amount = destination_amount if destination_amount > ZERO else origin_amount
                fee_amount = (
                    abs(origin_amount - destination_amount) if destination_amount > ZERO else ZERO
                )
            else:
                raise DeserializationError(
                    f'Unknown Bit2me transaction type: {transaction_type}. '
                    f'Raw movement: {raw_movement}',
                )

            # Parse timestamp from ISO format using shared utility
            timestamp_sec = deserialize_timestamp_from_date(
                raw_movement['date'], 'iso8601', 'bit2me',
            )
            timestamp_ms = TimestampMS(ts_sec_to_ms(timestamp_sec))

            # Resolve asset
            asset = asset_from_bit2me(asset_symbol)

            # Extract transaction ID and method
            movement_id = raw_movement['id']

            # Build extra data with address if available
            extra_data: AssetMovementExtraData | None = None
            if address and address != 'null' and address is not None:
                extra_data = maybe_set_transaction_extra_data(
                    address=address,
                    transaction_id=None,  # Bit2me doesn't provide txid in this endpoint
                    extra_data=None,
                )

            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_type=event_type,
                timestamp=timestamp_ms,
                asset=asset,
                amount=amount,
                fee=AssetAmount(asset=asset, amount=fee_amount),
                unique_id=movement_id,
                extra_data=extra_data,
            )

        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me movement: {e}. Raw movement: {raw_movement}',
            ) from e
