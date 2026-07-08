import logging
import urllib.parse
from collections import defaultdict
from collections.abc import Callable, Sequence
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, TypeVar

import requests

from rotkehlchen.assets.converters import asset_from_coinex
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin, get_key_if_has_val
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
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
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
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

API_MAX_LIMIT: Final = 100
API_SUCCESS_CODE: Final = 0
COINEX_BASE_URL: Final = 'https://api.coinex.com/v2'
FINISHED_STATUS: Final = 'finished'
T = TypeVar('T', AssetMovement, SwapEvent)


class CoinexMarket(NamedTuple):
    market: str
    base_asset_symbol: str
    quote_asset_symbol: str
    base_asset: 'AssetWithOracles'
    quote_asset: 'AssetWithOracles'


class Coinex(ExchangeInterface, SignatureGeneratorMixin):
    """CoinEx exchange API docs: https://docs.coinex.com/api/v2/"""

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ):
        super().__init__(
            name=name,
            location=Location.COINEX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = COINEX_BASE_URL

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _generate_signature(
            self,
            method: Literal['GET'],
            request_path: str,
            timestamp: str,
            body: str = '',
    ) -> str:
        return self.generate_hmac_signature(
            message=f'{method}{request_path}{body}{timestamp}',
            encoding='latin-1',
        ).lower()

    def _api_query(
            self,
            endpoint: Literal[
                '/assets/spot/balance',
                '/assets/deposit-history',
                '/assets/withdraw',
                '/spot/finished-order',
                '/spot/market',
            ],
            options: dict[str, Any] | None = None,
            signed: bool = True,
    ) -> Any:
        """Request a CoinEx API endpoint.

        May raise RemoteError.
        """
        options = options.copy() if options else {}
        query_string = urllib.parse.urlencode(options)
        request_path = f'/v2{endpoint}'
        if query_string:
            request_path = f'{request_path}?{query_string}'

        request_url = f'{self.base_uri}{endpoint}'
        headers = {}
        if signed:
            timestamp = str(ts_now_in_ms())
            headers = {
                'X-COINEX-KEY': self.api_key,
                'X-COINEX-SIGN': self._generate_signature(
                    method='GET',
                    request_path=request_path,
                    timestamp=timestamp,
                ),
                'X-COINEX-TIMESTAMP': timestamp,
            }

        log.debug('CoinEx API request', request_url=request_url, options=options)
        try:
            response = self.session.get(
                url=request_url,
                params=options,
                headers=headers,
                timeout=CachedSettings().get_timeout_tuple(),
            )
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'CoinEx request at {request_url} connection error: {e!s}.') from e
        except JSONDecodeError as e:
            raise RemoteError(f'CoinEx request at {request_url} returned invalid JSON.') from e

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'CoinEx request at {request_url} responded with HTTP status '
                f'{response.status_code}: {response.text}',
            )

        if response_data.get('code') != API_SUCCESS_CODE:
            raise RemoteError(
                f'CoinEx request at {request_url} failed with code '
                f'{response_data.get("code")}: {response_data.get("message")}',
            )

        if 'data' not in response_data:
            raise RemoteError(f'CoinEx request at {request_url} is missing data in response.')

        return response_data['data']

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the CoinEx API key can access account information."""
        try:
            self._api_query(endpoint='/assets/spot/balance')
        except RemoteError as e:
            return False, str(e)
        return True, ''

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query spot balances linked to the API key."""
        try:
            balances = self._api_query(endpoint='/assets/spot/balance')
        except RemoteError as e:
            log.error(f'Failed to query CoinEx balances due to {e!s}')
            return None, f'Failed to query CoinEx balances due to a remote error: {e!s}'

        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        for balance in balances:
            try:
                amount = (
                    deserialize_fval(balance['available']) +
                    deserialize_fval(balance['frozen'])
                )
                if amount == ZERO:
                    continue

                asset = asset_from_coinex(balance['ccy'])
            except (DeserializationError, KeyError) as e:
                log.error(f'Failed to deserialize CoinEx balance {balance}. {e!s}')
                self.msg_aggregator.add_error(
                    'Failed to deserialize a CoinEx balance entry. '
                    'Check logs for details. Ignoring it.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

            amounts[asset] += amount

        return dict(self.balances_from_amounts(amounts)), ''

    def _query_markets(self) -> list[CoinexMarket]:
        """Query and deserialize CoinEx spot markets."""
        markets = []
        try:
            raw_markets = self._api_query(endpoint='/spot/market', signed=False)
        except RemoteError as e:
            log.error(f'Failed to query CoinEx markets due to {e!s}')
            self.msg_aggregator.add_error(f'Got remote error while querying CoinEx markets: {e!s}')
            return []

        for entry in raw_markets:
            try:
                markets.append(CoinexMarket(
                    market=entry['market'],
                    base_asset_symbol=entry['base_ccy'],
                    quote_asset_symbol=entry['quote_ccy'],
                    base_asset=asset_from_coinex(entry['base_ccy']),
                    quote_asset=asset_from_coinex(entry['quote_ccy']),
                ))
            except (DeserializationError, KeyError) as e:
                log.error(f'Failed to deserialize CoinEx market {entry}. {e!s}')
            except UnknownAsset as e:
                log.debug(f'Found CoinEx market with unknown asset {e.identifier}. Skipping.')

        return markets

    def _deserialize_trade(
            self,
            trade: dict[str, Any],
            market: CoinexMarket,
    ) -> list[SwapEvent]:
        """Deserialize a CoinEx finished order into swap events."""
        spend, receive = get_swap_spend_receive(
            is_buy=deserialize_trade_type_is_buy(trade['side']),
            base_asset=market.base_asset,
            quote_asset=market.quote_asset,
            amount=deserialize_fval(trade['filled_amount']),
            rate=deserialize_price(deserialize_fval(trade['filled_value']) / deserialize_fval(
                trade['filled_amount'],
            )),
        )
        base_fee = deserialize_fval_or_zero(trade['base_fee'])
        quote_fee = deserialize_fval_or_zero(trade['quote_fee'])
        fee_asset = market.base_asset if base_fee != ZERO else market.quote_asset
        return create_swap_events(
            timestamp=deserialize_timestamp_ms_from_intms(trade['created_at']),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=fee_asset,
                amount=base_fee if base_fee != ZERO else quote_fee,
            ),
            location_label=self.name,
            group_identifier=create_group_identifier_from_unique_id(
                location=self.location,
                unique_id=f'trade-{trade["order_id"]}',
            ),
        )

    def _deserialize_asset_movement(
            self,
            movement: dict[str, Any],
            movement_type: Literal['deposit', 'withdrawal'],
    ) -> list[AssetMovement]:
        """Deserialize a CoinEx deposit or withdrawal into asset movement events."""
        asset = asset_from_coinex(movement['ccy'])
        return create_asset_movement_with_fee(
            timestamp=deserialize_timestamp_ms_from_intms(movement['created_at']),
            location=self.location,
            location_label=self.name,
            event_subtype=(
                HistoryEventSubType.RECEIVE
                if movement_type == 'deposit' else
                HistoryEventSubType.SPEND
            ),
            asset=asset,
            amount=deserialize_fval(movement['amount']),
            fee=AssetAmount(
                asset=asset,
                amount=deserialize_fval_or_zero(movement['tx_fee']),
            ) if movement_type == 'withdrawal' else None,
            unique_id=(
                f'deposit-{movement["deposit_id"]}'
                if movement_type == 'deposit' else
                f'withdrawal-{movement["withdraw_id"]}'
            ),
            extra_data=maybe_set_transaction_extra_data(
                address=get_key_if_has_val(movement, 'to_address'),
                transaction_id=get_key_if_has_val(movement, 'tx_id'),
            ),
        )

    def _api_query_paginated(
            self,
            endpoint: Literal[
                '/spot/finished-order',
                '/assets/deposit-history',
                '/assets/withdraw',
            ],
            options: dict[str, Any],
            deserialization_method: Callable[[dict[str, Any]], list[T]],
    ) -> list[T]:
        results: list[T] = []
        page = 1
        while True:
            query_options = options.copy()
            query_options['page'] = page
            query_options['limit'] = API_MAX_LIMIT
            try:
                data = self._api_query(endpoint=endpoint, options=query_options)
            except RemoteError as e:
                log.error(f'CoinEx {endpoint} query failed due to a remote error: {e!s}')
                self.msg_aggregator.add_error(f'Got remote error while querying CoinEx: {e!s}')
                return results

            if not isinstance(data, list):
                log.error(f'CoinEx {endpoint} returned unexpected data: {data}')
                self.msg_aggregator.add_error(
                    f'Failed to load CoinEx {endpoint}. Check logs for details.',
                )
                return results

            for entry in data:
                try:
                    results.extend(deserialization_method(entry))
                except (DeserializationError, KeyError) as e:
                    msg = f'Missing key {e}' if isinstance(e, KeyError) else str(e)
                    log.error(f'CoinEx {endpoint} {msg}: {entry}')
                    self.msg_aggregator.add_error(msg)
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details=f'{endpoint} query',
                    )

            if len(data) < API_MAX_LIMIT:
                break

            page += 1

        return results

    def _query_asset_movements(
            self,
            movement_type: Literal['deposit', 'withdrawal'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        endpoint: Literal['/assets/deposit-history', '/assets/withdraw'] = (
            '/assets/deposit-history' if movement_type == 'deposit' else '/assets/withdraw'
        )
        start_ts_ms, end_ts_ms = ts_sec_to_ms(start_ts), ts_sec_to_ms(end_ts)
        return self._api_query_paginated(
            endpoint=endpoint,
            options={'status': FINISHED_STATUS},
            deserialization_method=lambda entry: (
                self._deserialize_asset_movement(movement=entry, movement_type=movement_type)
                if start_ts_ms <= int(entry['created_at']) <= end_ts_ms else
                []
            ),
        )

    def _query_trades(self, start_ts: Timestamp, end_ts: Timestamp) -> list[SwapEvent]:
        events = []
        markets = {market.market: market for market in self._query_markets()}
        start_ts_ms, end_ts_ms = ts_sec_to_ms(start_ts), ts_sec_to_ms(end_ts)
        events.extend(self._api_query_paginated(
            endpoint='/spot/finished-order',
            options={
                'market_type': 'SPOT',
                'start_time': start_ts_ms,
                'end_time': end_ts_ms,
            },
            deserialization_method=lambda entry: self._deserialize_trade(
                trade=entry,
                market=markets[entry['market']],
            ),
        ))

        return events

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        events: list[AssetMovement | SwapEvent] = []
        events.extend(self._query_asset_movements(
            movement_type='deposit',
            start_ts=start_ts,
            end_ts=end_ts,
        ))
        events.extend(self._query_asset_movements(
            movement_type='withdrawal',
            start_ts=start_ts,
            end_ts=end_ts,
        ))
        events.extend(self._query_trades(start_ts=start_ts, end_ts=end_ts))
        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for CoinEx
