import logging
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode

import requests

from rotkehlchen.assets.converters import asset_from_bitget
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError, cause_for_status, credential_check_cause_of
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import (
    ApiKeyCheck,
    ExchangeInterface,
    ExchangeQueryBalances,
    HistoryEventQueue,
)
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.fval import FVal
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
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.locations.constants import LOCATION_BITGET
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_now_in_ms, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITGET_BASE_URL: Final = 'https://api.bitget.com'
BITGET_LAUNCH_TS: Final = Timestamp(1530403200)  # July 2018
BITGET_MAX_HISTORY_WINDOW: Final = 90 * DAY_IN_SECONDS
BITGET_MAX_RESULTS: Final = 100
BITGET_PRODUCT_TYPES: Final = ('USDT-FUTURES', 'COIN-FUTURES', 'USDC-FUTURES')

BitgetEndpoint = Literal[
    '/api/v2/spot/account/assets',
    '/api/v2/spot/public/symbols',
    '/api/v2/spot/trade/fills',
    '/api/v2/spot/wallet/deposit-records',
    '/api/v2/spot/wallet/withdrawal-records',
    '/api/v2/mix/account/accounts',
    '/api/v2/mix/position/history-position',
]


class Bitget(ExchangeInterface, SignatureGeneratorMixin):
    """Bitget classic account integration using its v2 read-only REST API."""

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            passphrase: str,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=LOCATION_BITGET,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.passphrase = passphrase
        self.base_uri = BITGET_BASE_URL
        self.symbols: dict[str, tuple[AssetWithOracles, AssetWithOracles]] = {}
        self.session.headers.update({
            'ACCESS-KEY': self.api_key,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
            'locale': 'en-US',
        })

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'ACCESS-KEY': self.api_key})
        if credentials.passphrase is not None:
            self.passphrase = credentials.passphrase
            self.session.headers.update({'ACCESS-PASSPHRASE': self.passphrase})
        return changed

    def _generate_signature(self, timestamp: str, request_path: str) -> str:
        return self.generate_hmac_b64_signature(f'{timestamp}GET{request_path}')

    def _api_query(
            self,
            endpoint: BitgetEndpoint,
            options: dict[str, Any] | None = None,
    ) -> Any:
        options = options or {}
        request_path: str = endpoint
        if len(query_string := urlencode(options)) != 0:
            request_path = f'{request_path}?{query_string}'

        request_url = f'{self.base_uri}{endpoint}'
        timestamp = str(ts_now_in_ms())
        log.debug('Bitget API request', endpoint=endpoint, options=options)
        try:
            response = self.session.get(
                url=request_url,
                params=options,
                headers={
                    'ACCESS-SIGN': self._generate_signature(timestamp, request_path),
                    'ACCESS-TIMESTAMP': timestamp,
                },
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(
                f'Bitget request at {request_url} failed due to {e!s}',
                cause=FailureCause.NETWORK,
            ) from e

        try:
            response_data = response.json()
        except JSONDecodeError as e:
            raise RemoteError(
                f'Bitget request at {request_url} returned invalid JSON with HTTP status '
                f'{response.status_code}',
                cause=FailureCause.BAD_DATA,
            ) from e

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Bitget request at {request_url} failed with HTTP status '
                f'{response.status_code}: {response_data.get("msg", response.text)}',
                cause=cause_for_status(response.status_code),
            )
        if response_data.get('code') != '00000':
            raise RemoteError(
                f'Bitget request at {request_url} failed with error code '
                f'{response_data.get("code")}: {response_data.get("msg")}',
                cause=FailureCause.REMOTE_REJECTED,
            )
        if 'data' not in response_data:
            raise RemoteError(
                f'Bitget request at {request_url} returned no data',
                cause=FailureCause.BAD_DATA,
            )
        return response_data['data']

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        try:
            raw_symbols = self._api_query('/api/v2/spot/public/symbols')
        except RemoteError as e:
            log.error('Failed to query Bitget symbols due to %s', e)
            return

        for entry in raw_symbols:
            try:
                self.symbols[entry['symbol']] = (
                    asset_from_bitget(entry['baseCoin']),
                    asset_from_bitget(entry['quoteCoin']),
                )
            except (KeyError, UnknownAsset, UnsupportedAsset):
                continue
        self.first_connection_made = True

    def validate_api_key(self) -> ApiKeyCheck:
        try:
            self._api_query('/api/v2/spot/account/assets')
        except RemoteError as e:
            return ApiKeyCheck(False, str(e), credential_check_cause_of(e))
        return ApiKeyCheck(True)

    def _add_balance_entries(
            self,
            amounts: defaultdict[AssetWithOracles, FVal],
            entries: Sequence[dict[str, Any]],
            amount_keys: tuple[str, ...],
    ) -> None:
        for entry in entries:
            try:
                asset = asset_from_bitget(entry['coin'])
                amount = sum(
                    (deserialize_fval(entry.get(key, '0')) for key in amount_keys),
                    start=ZERO,
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(e.identifier, 'balance query')
                continue
            except (DeserializationError, KeyError, TypeError) as e:
                log.error('Failed to deserialize Bitget balance %s due to %s', entry, e)
                continue
            if amount != ZERO:
                amounts[asset] += amount

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        try:
            self._add_balance_entries(
                amounts=amounts,
                entries=self._api_query('/api/v2/spot/account/assets'),
                amount_keys=('available', 'frozen', 'locked'),
            )
            for product_type in BITGET_PRODUCT_TYPES:
                futures_accounts = self._api_query(
                    '/api/v2/mix/account/accounts',
                    {'productType': product_type},
                )
                for account in futures_accounts:
                    if account.get('assetMode') == 'union':
                        self._add_balance_entries(
                            amounts=amounts,
                            entries=account.get('assetList', []),
                            amount_keys=('balance',),
                        )
                    else:
                        self._add_balance_entries(
                            amounts=amounts,
                            entries=[{'coin': account.get('marginCoin'), 'equity': account.get('accountEquity', '0')}],  # noqa: E501
                            amount_keys=('equity',),
                        )
        except RemoteError as e:
            msg = f'Bitget balance query failed due to {e!s}'
            log.error(msg)
            return ExchangeQueryBalances(None, msg, e.cause)

        return ExchangeQueryBalances(dict(self.balances_from_amounts(amounts)), '')

    def _paginated_query(
            self,
            endpoint: BitgetEndpoint,
            options: dict[str, Any],
            id_key: str,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        query_options = {**options, 'limit': BITGET_MAX_RESULTS}
        while True:
            page = self._api_query(endpoint, query_options)
            if isinstance(page, dict):
                entries = page.get('list', [])
                next_id = page.get('endId')
            else:
                entries = page
                next_id = entries[-1].get(id_key) if len(entries) != 0 else None
            results.extend(entries)
            if len(entries) < BITGET_MAX_RESULTS or next_id is None:
                break
            query_options['idLessThan'] = next_id
        return results

    def _query_spot_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue | None,
    ) -> list[SwapEvent]:
        self.first_connection()
        events: list[SwapEvent] = []
        for window_start, window_end in self._history_windows(
                Timestamp(max(start_ts, ts_now() - BITGET_MAX_HISTORY_WINDOW)), end_ts,
        ):
            page_events: list[SwapEvent] = []
            for entry in self._paginated_query(
                    '/api/v2/spot/trade/fills',
                    {
                        'startTime': ts_sec_to_ms(window_start),
                        'endTime': ts_sec_to_ms(window_end),
                    },
                    'tradeId',
            ):
                try:
                    base_asset, quote_asset = self.symbols[entry['symbol']]
                    spend, receive = get_swap_spend_receive(
                        is_buy=deserialize_trade_type_is_buy(entry['side']),
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        amount=deserialize_fval(entry['size']),
                        rate=deserialize_price(entry['priceAvg']),
                    )
                    fee_data = entry.get('feeDetail') or {}
                    fee_amount = abs(deserialize_fval(fee_data.get('totalFee', '0')))
                    page_events.extend(create_swap_events(
                        timestamp=TimestampMS(int(entry['cTime'])),
                        location=self.location,
                        location_label=self.name,
                        spend=spend,
                        receive=receive,
                        fee=AssetAmount(
                            asset=asset_from_bitget(fee_data['feeCoin']),
                            amount=fee_amount,
                        ) if fee_amount != ZERO else None,
                        group_identifier=create_group_identifier_from_unique_id(
                            location=self.location,
                            unique_id=entry['tradeId'],
                        ),
                    ))
                except (DeserializationError, KeyError, UnknownAsset, UnsupportedAsset, ValueError) as e:  # noqa: E501
                    log.error('Failed to deserialize Bitget trade %s due to %s', entry, e)
            if event_queue is None:
                events.extend(page_events)
            else:
                event_queue.flush(page_events)
        return events

    @staticmethod
    def _history_windows(
            start_ts: Timestamp,
            end_ts: Timestamp,
            window_size: int = BITGET_MAX_HISTORY_WINDOW,
    ) -> list[tuple[Timestamp, Timestamp]]:
        windows = []
        window_start = Timestamp(max(start_ts, BITGET_LAUNCH_TS))
        while window_start < end_ts:
            window_end = Timestamp(min(window_start + window_size, end_ts))
            windows.append((window_start, window_end))
            window_start = window_end
        return windows

    def _query_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_type: HistoryEventType,
    ) -> list[AssetMovement]:
        is_deposit = event_type == HistoryEventType.DEPOSIT
        endpoint: BitgetEndpoint = (
            '/api/v2/spot/wallet/deposit-records' if is_deposit else
            '/api/v2/spot/wallet/withdrawal-records'
        )
        events = []
        for window_start, window_end in self._history_windows(start_ts, end_ts):
            for entry in self._paginated_query(
                    endpoint,
                    {
                        'startTime': ts_sec_to_ms(window_start),
                        'endTime': ts_sec_to_ms(window_end),
                    },
                    'orderId',
            ):
                if entry.get('status') != 'success':
                    continue
                try:
                    asset = asset_from_bitget(entry['coin'])
                    events.extend(create_asset_movement_with_fee(
                        timestamp=TimestampMS(int(entry['uTime'])),
                        location=self.location,
                        location_label=self.name,
                        event_subtype=(
                            HistoryEventSubType.RECEIVE if is_deposit else
                            HistoryEventSubType.SPEND
                        ),
                        asset=asset,
                        amount=deserialize_fval(entry['size']),
                        fee=None if is_deposit else AssetAmount(
                            asset=asset,
                            amount=abs(deserialize_fval(entry.get('fee', '0'))),
                        ),
                        unique_id=entry['orderId'],
                        extra_data=maybe_set_transaction_extra_data(
                            address=entry.get('toAddress'),
                            transaction_id=entry.get('tradeId'),
                        ),
                    ))
                except (DeserializationError, KeyError, UnknownAsset, UnsupportedAsset, ValueError) as e:  # noqa: E501
                    log.error('Failed to deserialize Bitget movement %s due to %s', entry, e)
        return events

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
            event_queue: HistoryEventQueue | None = None,
    ) -> tuple[Sequence[HistoryBaseEntry], Timestamp]:
        events: list[AssetMovement | SwapEvent] = []
        for event_type in (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL):
            source_events = self._query_movements(start_ts, end_ts, event_type)
            if event_queue is None:
                events.extend(source_events)
            else:
                event_queue.flush(source_events)
        events.extend(self._query_spot_trades(start_ts, end_ts, event_queue))
        return events, end_ts

    def query_online_history_events_into_queue(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
    ) -> Timestamp:
        self.query_online_history_events(start_ts, end_ts, event_queue=event_queue)
        return end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        positions = []
        earliest_ts = Timestamp(max(start_ts, ts_now() - 90 * DAY_IN_SECONDS))
        for product_type in BITGET_PRODUCT_TYPES:
            for entry in self._paginated_query(
                    '/api/v2/mix/position/history-position',
                    {
                        'productType': product_type,
                        'startTime': ts_sec_to_ms(earliest_ts),
                        'endTime': ts_sec_to_ms(end_ts),
                    },
                    'positionId',
            ):
                try:
                    fee = abs(deserialize_fval(entry.get('openFee', '0'))) + abs(
                        deserialize_fval(entry.get('closeFee', '0')),
                    )
                    positions.append(MarginPosition(
                        location=self.location,
                        open_time=ts_ms_to_sec(TimestampMS(int(entry['ctime']))),
                        close_time=ts_ms_to_sec(TimestampMS(int(entry['utime']))),
                        profit_loss=deserialize_fval(entry['pnl']) + deserialize_fval(
                            entry.get('totalFunding', '0'),
                        ),
                        pl_currency=(asset := asset_from_bitget(entry['marginCoin'])),
                        fee=fee,
                        fee_currency=asset,
                        link=entry['positionId'],
                        notes=(
                            f'{entry.get("holdSide", "").capitalize()} {entry["symbol"]} '
                            f'{entry.get("marginMode", "")} futures position'
                        ),
                    ))
                except (DeserializationError, KeyError, UnknownAsset, UnsupportedAsset, ValueError) as e:  # noqa: E501
                    log.error(
                        'Failed to deserialize Bitget margin position %s due to %s', entry, e,
                    )
        return positions
