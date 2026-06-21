import base64
import hashlib
import json
import logging
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode

import requests
from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_bit2me
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
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
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
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
from rotkehlchen.utils.misc import (
    timestamp_to_iso8601,
    ts_ms_to_sec,
    ts_now_in_ms,
    ts_sec_to_ms,
)
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Max page size accepted by each endpoint (per Bit2me API docs).
API_TRADES_MAX_LIMIT: Final = 50
API_TRANSACTIONS_MAX_LIMIT: Final = 100


class Bit2me(ExchangeInterface, SignatureGeneratorMixin):
    """Bit2me exchange API implementation.

    API gateway and auth follow the official samples at
    https://github.com/bit2me-devs/trading-spot-samples
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
        self.base_uri = 'https://gateway.bit2me.com'
        self.session.headers.update({
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
        })
        self.nonce_lock = Semaphore()

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'x-api-key': self.api_key})
        return changed

    def first_connection(self) -> None:
        """Bit2me does not require prefetching markets or metadata before use."""
        if not self.first_connection_made:
            self.first_connection_made = True

    def validate_api_key(self) -> tuple[bool, str]:
        """Validate Bit2me API credentials by querying a minimal private endpoint."""
        try:
            self._api_query('balances')
        except RemoteError as e:
            return False, str(e)

        return True, ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> list[MarginPosition]:
        """Bit2me does not provide margin positions."""
        return []

    def _generate_signature(
            self,
            path: str,
            body: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Generate the authentication signature for a Bit2me API request.

        Following the official sample implementation:
        - nonce = current time in milliseconds
        - message = "nonce:path" or "nonce:path:compact_json_body"
        - signature = base64(hmac_sha512(secret, sha256(message)))

        Returns a tuple of (nonce, signature).
        """
        nonce = str(ts_now_in_ms())
        if body:  # compact JSON (no spaces) as in the official sample
            message = f'{nonce}:{path}:{json.dumps(body, separators=(",", ":"))}'
        else:
            message = f'{nonce}:{path}'
        sha256_digest = hashlib.sha256(message.encode()).digest()
        signature = base64.b64encode(bytes.fromhex(self.generate_hmac_signature(
            sha256_digest,
            digest_algorithm=hashlib.sha512,
        ))).decode()
        return nonce, signature

    def _api_query(
            self,
            endpoint: Literal['balances', 'trades', 'transactions'],
            options: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Request a Bit2me API endpoint.

        May raise:
        - RemoteError: if the request fails or the API returns an error status.
        """
        api_path = {
            'balances': '/v1/wallet/pocket',
            'trades': '/v1/trading/trade',
            'transactions': '/v2/wallet/transaction',
        }[endpoint]
        request_url = f'{self.base_uri}{api_path}'
        if options:
            request_url += f'?{urlencode(options)}'

        with self.nonce_lock:
            # the signed path must include the query string
            nonce, signature = self._generate_signature(request_url.replace(self.base_uri, ''))
            auth_headers = {
                'api-signature': signature,
                'x-nonce': nonce,
            }
            log.debug('Bit2me API request', request_url=request_url)
            try:
                response = self.session.get(url=request_url, headers=auth_headers)
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} GET request at {request_url} connection error: {e!s}.',
                ) from e

        if response.status_code != HTTPStatus.OK:
            self._process_error_response(response)

        return response

    def _process_error_response(self, response: requests.Response) -> None:
        """Always raises RemoteError with an appropriate message from the API response."""
        try:
            error_message = jsonloads_dict(response.text).get('message', response.text)
        except JSONDecodeError:
            error_message = response.text

        log.error(
            'Bit2me API error',
            status_code=response.status_code,
            error=error_message,
        )
        raise RemoteError(f'{self.name} API error: {error_message}')

    @protect_with_lock()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query Bit2me pocket balances for all assets."""
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

        # The pocket endpoint returns a list of pockets. A currency can have more than one
        # pocket (e.g. "BTC 1", "BTC 2"), so balances are accumulated per asset.
        assets_balance: dict[AssetWithOracles, Balance] = defaultdict(Balance)
        for balance_entry in response_data:
            try:
                if (asset_symbol := balance_entry.get('currency')) is None:
                    log.warning('Bit2me balance entry missing currency symbol: %s', balance_entry)
                    continue

                try:
                    asset = asset_from_bit2me(asset_symbol)
                except (UnknownAsset, UnsupportedAsset) as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported Bit2me asset {asset_symbol}. '
                        f'{e!s}. Ignoring its balance.',
                    )
                    continue

                total_amount = (
                    deserialize_fval(
                        value=balance_entry.get('balance', '0'),
                        name='balance',
                        location='bit2me',
                    ) + deserialize_fval(
                        value=balance_entry.get('blockedBalance', '0'),
                        name='blockedBalance',
                        location='bit2me',
                    ) + deserialize_fval(
                        value=balance_entry.get('blockedOutputBalance', '0'),
                        name='blockedOutputBalance',
                        location='bit2me',
                    )
                )
                if total_amount == ZERO:
                    continue

                try:
                    usd_price = Inquirer.find_usd_price(asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing Bit2me balance entry for {asset_symbol} due to '
                        f'inability to query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                assets_balance[asset] += Balance(
                    amount=total_amount,
                    value=total_amount * usd_price,
                )
            except DeserializationError as e:
                log.error('Error processing Bit2me balance entry %s. %s', balance_entry, e)
                self.msg_aggregator.add_error(
                    f'Failed to deserialize a Bit2me balance. {e!s}. Check logs for details.',
                )
                continue

        return dict(assets_balance), ''

    def _query_transactions(self) -> list[dict[str, Any]]:
        """Query all transactions from /v2/wallet/transaction, paginating through every page.

        The endpoint has no time-range filter, so the full history is fetched once and the
        callers dispatch each transaction to the relevant handler.

        May raise:
        - RemoteError: if a request fails or the API returns invalid JSON.
        """
        all_transactions: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self._api_query('transactions', options={
                'offset': offset,
                'limit': API_TRANSACTIONS_MAX_LIMIT,
            })
            try:
                response_data = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'{self.name} returned invalid JSON for transactions. {e!s}',
                ) from e

            page = response_data.get('data', [])
            all_transactions.extend(page)
            offset += len(page)
            total = response_data.get('total')
            if (
                len(page) < API_TRANSACTIONS_MAX_LIMIT or
                (total is not None and offset >= total)
            ):
                break

        return all_transactions

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,  # pylint: disable=unused-argument
    ) -> tuple['Sequence[HistoryBaseEntry]', Timestamp]:
        """Query all history events from Bit2me.

        Combines asset movements (deposits/withdrawals), brokerage trades, EARN (staking)
        movements and airdrops -- all derived from a single transactions fetch -- together
        with spot trades from /v1/trading/trade.
        """
        events: list[HistoryBaseEntry] = []
        try:
            transactions = self._query_transactions()
        except RemoteError as e:
            self.msg_aggregator.add_error(f'Failed to query {self.name} transactions. {e!s}')
            transactions = []

        events.extend(self._build_asset_movements(transactions, start_ts, end_ts))
        events.extend(self._build_brokerage_trades(transactions, start_ts, end_ts))
        events.extend(self._build_earn_movements(transactions, start_ts, end_ts))
        events.extend(self._build_airdrops(transactions, start_ts, end_ts))
        events.extend(self.query_online_trade_history(start_ts, end_ts)[0])
        return events, end_ts

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query Bit2me deposits and withdrawals within a time range."""
        try:
            transactions = self._query_transactions()
        except RemoteError as e:
            self.msg_aggregator.add_error(f'Failed to query {self.name} transactions. {e!s}')
            return []

        return self._build_asset_movements(transactions, start_ts, end_ts)

    def _query_brokerage_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Query Bit2me brokerage trades (direct purchases) within a time range."""
        try:
            transactions = self._query_transactions()
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query {self.name} brokerage transactions. {e!s}',
            )
            return []

        return self._build_brokerage_trades(transactions, start_ts, end_ts)

    def _query_earn_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Query Bit2me EARN (staking) movements within a time range."""
        try:
            transactions = self._query_transactions()
        except RemoteError as e:
            self.msg_aggregator.add_error(f'Failed to query {self.name} EARN transactions. {e!s}')
            return []

        return self._build_earn_movements(transactions, start_ts, end_ts)

    def _query_airdrops(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Query Bit2me airdrops (social-pay gifts) within a time range."""
        try:
            transactions = self._query_transactions()
        except RemoteError as e:
            self.msg_aggregator.add_error(f'Failed to query {self.name} airdrop transactions. {e!s}')  # noqa: E501
            return []

        return self._build_airdrops(transactions, start_ts, end_ts)

    def _build_asset_movements(
            self,
            transactions: list[dict[str, Any]],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        movements: list[AssetMovement] = []
        for raw_transaction in transactions:
            try:
                movement_events = self._deserialize_asset_movement(raw_transaction)
            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                log.error('Failed to deserialize Bit2me transaction', error=str(e), raw_transaction=raw_transaction)  # noqa: E501
                self.msg_aggregator.add_error(
                    f'Failed to process a {self.name} transaction. Check logs for details.',
                )
                continue

            if movement_events is None:
                continue

            if start_ts <= ts_ms_to_sec(movement_events[0].timestamp) <= end_ts:
                movements.extend(movement_events)

        return movements

    def _build_brokerage_trades(
            self,
            transactions: list[dict[str, Any]],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        brokerage_trades: list[SwapEvent] = []
        for raw_transaction in transactions:
            if (
                raw_transaction.get('type') != 'transfer' or
                raw_transaction.get('subtype') != 'purchase'
            ):
                continue

            try:
                trade_events = self._deserialize_brokerage_trade(raw_transaction)
            except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                log.error('Failed to deserialize Bit2me brokerage trade', error=str(e), raw_transaction=raw_transaction)  # noqa: E501
                self.msg_aggregator.add_error(
                    f'Failed to process a {self.name} brokerage trade. Check logs for details.',
                )
                continue

            if trade_events and start_ts <= ts_ms_to_sec(trade_events[0].timestamp) <= end_ts:
                brokerage_trades.extend(trade_events)

        return brokerage_trades

    def _build_earn_movements(
            self,
            transactions: list[dict[str, Any]],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        earn_events: list[HistoryEvent] = []
        for raw_transaction in transactions:
            if (
                raw_transaction.get('subtype') != 'earn' or
                raw_transaction.get('status') != 'completed'
            ):
                continue

            if (earn_event := self._deserialize_earn_movement(raw_transaction)) is None:
                continue

            if start_ts <= ts_ms_to_sec(earn_event.timestamp) <= end_ts:
                earn_events.append(earn_event)

        return earn_events

    def _build_airdrops(
            self,
            transactions: list[dict[str, Any]],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        airdrop_events: list[HistoryEvent] = []
        for raw_transaction in transactions:
            if (
                raw_transaction.get('type') != 'transfer' or
                raw_transaction.get('subtype') != 'social-pay' or
                raw_transaction.get('status') != 'completed'
            ):
                continue

            if (airdrop_event := self._deserialize_airdrop(raw_transaction)) is None:
                continue

            if start_ts <= ts_ms_to_sec(airdrop_event.timestamp) <= end_ts:
                airdrop_events.append(airdrop_event)

        return airdrop_events

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[SwapEvent], tuple[Timestamp, Timestamp]]:
        """Query Bit2me spot trade history within a time range.

        The /v1/trading/trade endpoint supports server-side startTime/endTime filtering and
        offset/limit pagination.
        """
        log.debug('Querying Bit2me trade history', start_ts=start_ts, end_ts=end_ts)
        swap_events: list[SwapEvent] = []
        offset = 0
        while True:
            try:
                response = self._api_query('trades', options={
                    'startTime': timestamp_to_iso8601(start_ts, utc_as_z=True),
                    'endTime': timestamp_to_iso8601(end_ts, utc_as_z=True),
                    'offset': offset,
                    'limit': API_TRADES_MAX_LIMIT,
                })
                response_data = jsonloads_dict(response.text)
            except RemoteError as e:
                self.msg_aggregator.add_error(f'Failed to query {self.name} trade history. {e!s}')
                break
            except JSONDecodeError as e:
                self.msg_aggregator.add_error(
                    f'{self.name} returned invalid JSON for trades. {e!s}',
                )
                break

            trades_list = response_data.get('data', [])
            for raw_trade in trades_list:
                try:
                    swap_events.extend(self._deserialize_trade(raw_trade))
                except (DeserializationError, UnknownAsset, UnsupportedAsset) as e:
                    log.error('Failed to deserialize Bit2me trade', error=str(e), raw_trade=raw_trade)  # noqa: E501
                    self.msg_aggregator.add_error(
                        f'Failed to process a {self.name} trade. Check logs for details.',
                    )

            offset += len(trades_list)
            total = response_data.get('count')
            if (
                len(trades_list) < API_TRADES_MAX_LIMIT or
                (total is not None and offset >= total)
            ):
                break

        return swap_events, (start_ts, end_ts)

    def _deserialize_trade(self, raw_trade: dict[str, Any]) -> list[SwapEvent]:
        """Deserialize a spot trade from the /v1/trading/trade response.

        May raise:
        - DeserializationError, UnknownAsset, UnsupportedAsset
        """
        try:
            timestamp_ms = TimestampMS(ts_sec_to_ms(deserialize_timestamp_from_date(
                raw_trade['createdAt'], 'iso8601', 'bit2me',
            )))
            if '/' not in (symbol := raw_trade['symbol']):
                raise DeserializationError(
                    f'Invalid Bit2me trading pair format: {symbol}. Expected format: BASE/QUOTE',
                )
            base_symbol, quote_symbol = symbol.split('/', 1)
            spend, receive = get_swap_spend_receive(
                is_buy=raw_trade['side'].lower() == 'buy',
                base_asset=asset_from_bit2me(base_symbol),
                quote_asset=asset_from_bit2me(quote_symbol),
                amount=deserialize_fval(raw_trade['amount']),
                rate=deserialize_price(raw_trade['price']),
            )
            return create_swap_events(
                spend=spend,
                receive=receive,
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                fee=AssetAmount(
                    asset=asset_from_bit2me(raw_trade.get('feeCurrency', quote_symbol)),
                    amount=deserialize_fval_or_zero(raw_trade.get('feeAmount', '0')),
                ),
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, str(raw_trade['id']),
                ),
            )
        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me trade: {e}. Raw trade: {raw_trade}',
            ) from e

    def _deserialize_brokerage_trade(
            self,
            raw_transaction: dict[str, Any],
    ) -> list[SwapEvent]:
        """Deserialize a brokerage purchase (type=transfer, subtype=purchase).

        These represent direct crypto purchases with fiat. The fee is the difference between
        what was spent and the value of what was received at the quoted exchange rate.

        May raise:
        - DeserializationError, UnknownAsset, UnsupportedAsset
        """
        try:
            timestamp_ms = TimestampMS(ts_sec_to_ms(deserialize_timestamp_from_date(
                raw_transaction['date'], 'iso8601', 'bit2me',
            )))
            origin = raw_transaction['origin']
            destination = raw_transaction['destination']
            spend_amount = deserialize_fval(origin['amount'])
            spend_asset = asset_from_bit2me(origin['currency'])
            receive_amount = deserialize_fval(destination['amount'])
            receive_asset = asset_from_bit2me(destination['currency'])

            # The destination rate is base/quote (e.g. BTC/EUR). The fee can only be derived
            # when the quote currency matches the spent currency, keeping units consistent.
            fee: AssetAmount | None = None
            dest_rate = destination.get('rate', {})
            if (
                (rate_value := dest_rate.get('value')) is not None and
                dest_rate.get('pair', {}).get('quote') == origin['currency'] and
                (fee_amount := spend_amount - receive_amount * deserialize_fval(rate_value)) > ZERO
            ):
                fee = AssetAmount(asset=spend_asset, amount=fee_amount)

            return create_swap_events(
                spend=AssetAmount(asset=spend_asset, amount=spend_amount),
                receive=AssetAmount(asset=receive_asset, amount=receive_amount),
                timestamp=timestamp_ms,
                location=self.location,
                location_label=self.name,
                fee=fee,
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, str(raw_transaction['id']),
                ),
            )
        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me brokerage trade: {e}. Raw transaction: {raw_transaction}',
            ) from e

    def _deserialize_earn_movement(
            self,
            raw_movement: dict[str, Any],
    ) -> HistoryEvent | None:
        """Deserialize an EARN (staking) movement.

        EARN movements are internal transfers between the pocket and the earn program. The
        direction is determined by the origin/destination class, not the transaction type:
        - destination.class == "earn" -> deposit into earn (DEPOSIT_ASSET)
        - origin.class == "earn" -> withdrawal from earn (REMOVE_ASSET)

        Returns None for movements that aren't recognised earn transfers.
        """
        try:
            origin = raw_movement.get('origin', {})
            destination = raw_movement.get('destination', {})
            if destination.get('class') == 'earn':
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                asset_symbol, amount_str = origin['currency'], origin['amount']
                notes_action = 'Deposit to'
            elif origin.get('class') == 'earn':
                event_subtype = HistoryEventSubType.REMOVE_ASSET
                asset_symbol, amount_str = destination['currency'], destination['amount']
                notes_action = 'Withdrawal from'
            else:
                log.warning('Unknown Bit2me EARN movement pattern: %s', raw_movement)
                return None

            amount = deserialize_fval(amount_str)
            return HistoryEvent(
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, raw_movement['id'],
                ),
                sequence_index=0,
                timestamp=TimestampMS(ts_sec_to_ms(deserialize_timestamp_from_date(
                    raw_movement['date'], 'iso8601', 'bit2me',
                ))),
                location=self.location,
                location_label=self.name,
                asset=asset_from_bit2me(asset_symbol),
                amount=amount,
                event_type=HistoryEventType.STAKING,
                event_subtype=event_subtype,
                notes=f'{notes_action} Bit2Me Earn: {amount} {asset_symbol}',
            )
        except (KeyError, DeserializationError, UnknownAsset, UnsupportedAsset) as e:
            log.warning('Failed to deserialize Bit2me EARN movement: %s. Movement: %s', e, raw_movement)  # noqa: E501
            return None

    def _deserialize_airdrop(
            self,
            raw_transaction: dict[str, Any],
    ) -> HistoryEvent | None:
        """Deserialize an airdrop/gift (social-pay) transaction.

        Social-pay transactions are gifts sent via email from Bit2me. Returns None if the
        transaction is not a valid airdrop.
        """
        try:
            destination = raw_transaction.get('destination', {})
            origin = raw_transaction.get('origin', {})
            asset_symbol = destination.get('currency', origin.get('currency'))
            amount = deserialize_fval(destination.get('amount', origin.get('amount', '0')))
            if amount <= ZERO:
                return None

            sender = origin.get('fullName', 'Bit2Me')
            method = raw_transaction.get('method', 'email')
            return HistoryEvent(
                group_identifier=create_group_identifier_from_unique_id(
                    self.location, raw_transaction['id'],
                ),
                sequence_index=0,
                timestamp=TimestampMS(ts_sec_to_ms(deserialize_timestamp_from_date(
                    raw_transaction['date'], 'iso8601', 'bit2me',
                ))),
                location=self.location,
                location_label=self.name,
                asset=asset_from_bit2me(asset_symbol),
                amount=amount,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.AIRDROP,
                notes=f'Airdrop from {sender}: {amount} {asset_symbol} via {method}',
            )
        except (KeyError, DeserializationError, UnknownAsset, UnsupportedAsset) as e:
            log.warning('Failed to deserialize Bit2me airdrop: %s. Transaction: %s', e, raw_transaction)  # noqa: E501
            return None

    def _deserialize_asset_movement(
            self,
            raw_movement: dict[str, Any],
    ) -> list[AssetMovement] | None:
        """Deserialize a deposit/withdrawal from a /v2/wallet/transaction entry.

        Returns None for transactions handled elsewhere (transfers handled as brokerage
        trades/airdrops/internal moves, and earn movements).

        May raise:
        - DeserializationError, UnknownAsset, UnsupportedAsset
        """
        try:
            # transfers (purchase/social-pay/internal) and earn movements are handled elsewhere
            if (
                (transaction_type := raw_movement.get('type')) not in ('deposit', 'withdrawal') or
                raw_movement.get('subtype') == 'earn'
            ):
                return None

            origin = raw_movement.get('origin', {})
            destination = raw_movement.get('destination', {})
            movement_subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.SPEND]
            if transaction_type == 'deposit':
                movement_subtype = HistoryEventSubType.RECEIVE
                asset_symbol = destination['currency']
                amount = deserialize_fval(destination['amount'])
                address = destination.get('address')
                origin_amount = deserialize_fval_or_zero(origin.get('amount', '0'))
                fee_amount = abs(origin_amount - amount) if origin_amount > ZERO else ZERO
            else:  # withdrawal
                movement_subtype = HistoryEventSubType.SPEND
                asset_symbol = origin['currency']
                origin_amount = deserialize_fval(origin['amount'])
                destination_amount = deserialize_fval_or_zero(destination.get('amount', '0'))
                address = destination.get('address')
                # the amount that actually arrives at the destination; the fee is the difference
                amount = destination_amount if destination_amount > ZERO else origin_amount
                fee_amount = (
                    abs(origin_amount - destination_amount) if destination_amount > ZERO else ZERO
                )

            asset = asset_from_bit2me(asset_symbol)
            extra_data: AssetMovementExtraData | None = None
            if address:
                extra_data = maybe_set_transaction_extra_data(
                    address=address,
                    transaction_id=None,  # not provided by this endpoint
                    extra_data=None,
                )

            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_subtype=movement_subtype,
                timestamp=TimestampMS(ts_sec_to_ms(deserialize_timestamp_from_date(
                    raw_movement['date'], 'iso8601', 'bit2me',
                ))),
                asset=asset,
                amount=amount,
                fee=AssetAmount(asset=asset, amount=fee_amount),
                unique_id=raw_movement['id'],
                extra_data=extra_data,
            )
        except KeyError as e:
            raise DeserializationError(
                f'Missing key in Bit2me movement: {e}. Raw movement: {raw_movement}',
            ) from e
