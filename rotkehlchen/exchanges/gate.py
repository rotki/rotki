from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.parse
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.assets.converters import asset_from_gate
from rotkehlchen.concurrency import result_of, spawn, wait
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.constants import GATE_LOCATION_KEY
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import (
    ExchangeInterface,
    ExchangeQueryBalances,
    ExchangeWithExtras,
)
from rotkehlchen.exchanges.utils import (
    SignatureGeneratorMixin,
    deserialize_asset_movement_address,
    get_key_if_has_val,
)
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events_multi_fee,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PAGINATION_LIMIT: Final = 1000
GATE_BASE_URL: Final = 'https://api.gateio.ws/api/v4'
GATE_MOVEMENTS_QUERY_START_TS: Final = Timestamp(1514764800)  # 2018-01-01
GATE_MAX_MOVEMENT_WINDOW: Final = 30 * DAY_IN_SECONDS
GATE_MOVEMENTS_PAGINATION_LIMIT: Final = 500


class GateLocation(SerializableEnumNameMixin):
    GLOBAL = GATE_BASE_URL
    EUROPE = 'https://api.gateeu.com/api/v4'
    US = 'https://api.gate.us/api/v4'


class Gate(ExchangeInterface, ExchangeWithExtras, SignatureGeneratorMixin):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            gate_location: GateLocation = GateLocation.GLOBAL,
    ):
        super().__init__(
            name=name,
            location=Location.GATE,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.gate_location = gate_location
        self.uri = gate_location.value
        self.session.headers.update({
            'Content-Type': 'application/json',
            'KEY': self.api_key,
        })

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed is True:
            self.session.headers.update({'KEY': self.api_key})

        return changed

    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        if (gate_location := extras.get(GATE_LOCATION_KEY)) is not None:
            self.gate_location = gate_location
            self.uri = gate_location.value

        return True, ''

    def _generate_signature(
            self,
            method: str,
            url_path: str,
            query_string: str,
            body: str,
    ) -> dict[str, str]:
        """Generate Gate v4 API signature headers.

        Signature payload: METHOD\nURL_PATH\nQUERY_STRING\nBODY_HASH\nTIMESTAMP
        """
        timestamp = str(time.time())
        body_hash = hashlib.sha512(body.encode('utf-8')).hexdigest()
        payload = f'{method}\n{url_path}\n{query_string}\n{body_hash}\n{timestamp}'
        signature = self.generate_hmac_signature(
            message=payload,
            digest_algorithm=hashlib.sha512,
        )
        return {
            'KEY': self.api_key,
            'Timestamp': timestamp,
            'SIGN': signature,
        }

    def _api_query(
            self,
            path: str,
            options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Query Gate API endpoint.

        May raise:
        - RemoteError
        """
        url = f'{self.uri}{path}'
        timeout = CachedSettings().get_timeout_tuple()
        method = 'GET'
        body = ''
        query_string = ''

        if options:
            query_string = urllib.parse.urlencode(options, quote_via=urllib.parse.quote)
            url = f'{url}?{query_string}'

        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=timeout,
                headers=self._generate_signature(
                    method=method,
                    url_path=urllib.parse.urlparse(url).path,
                    query_string=query_string,
                    body=body,
                ),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Gate API request failed due to {e}') from e

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise RemoteError(
                f'Gate api request for {response.url} failed with HTTP '
                f'status code {response.status_code} due to rate limiting',
            )

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Gate api request for {response.url} failed with HTTP status '
                f'code {response.status_code} and response {response.text}',
            )

        try:
            json_ret = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError('Gate returned invalid JSON response') from e

        if isinstance(json_ret, dict) and 'label' in json_ret:
            raise RemoteError(
                f'Gate returned error: {json_ret.get("message")} ({json_ret.get("label")})',
            )

        return json_ret

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Gate API key is good for usage in rotki"""
        try:
            self._api_query(path='/spot/accounts')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Query balances at Gate"""
        try:
            response = self._api_query(path='/spot/accounts')
        except RemoteError as e:
            msg = f'Gate request failed. Could not reach the exchange due to {e!s}'
            log.error(msg)
            return None, msg

        if not isinstance(response, list):
            log.error(f'Gate spot accounts response is not a list: {response}')
            return None, 'Unexpected response format from Gate'

        returned_balances: dict[AssetWithOracles, Balance] = {}
        for entry in response:
            try:
                asset = asset_from_gate(entry['currency'])
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except KeyError as e:
                log.error(f'Gate balance entry missing key {e}: {entry}')
                continue

            try:
                available = deserialize_fval(entry.get('available', '0'))
                locked = deserialize_fval(entry.get('locked', '0'))
                amount = available + locked
            except DeserializationError as e:
                log.error(f'Failed to deserialize Gate balance entry {entry}: {e}')
                continue

            if amount == ZERO:
                continue

            try:
                price = Inquirer.find_main_currency_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Gate balance entry due to inability to '
                    f'query price: {e!s}. Skipping balance entry',
                )
                continue

            returned_balances[asset] = Balance(
                amount=amount,
                value=amount * price,
            )

        return returned_balances, ''

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Query spot trades from Gate.

        Uses pagination via page/limit. Queries trades in time ranges using from/to
        parameters which are unix timestamps in seconds.
        """
        events: list[SwapEvent] = []
        page = 1

        while True:
            try:
                raw_data = self._api_query(
                    path='/spot/my_trades',
                    options={
                        'limit': PAGINATION_LIMIT,
                        'page': page,
                        'from': start_ts,
                        'to': end_ts,
                    },
                )
            except RemoteError as e:
                log.error(f'Failed to query Gate trades due to {e!s}')
                break

            if not isinstance(raw_data, list):
                log.error(f'Gate trades response is not a list: {raw_data}')
                break

            if len(raw_data) == 0:
                break

            for raw_trade in raw_data:
                try:
                    currency_pair = raw_trade['currency_pair']
                    side = raw_trade['side']
                    base_asset_str, quote_asset_str = currency_pair.split('_', maxsplit=1)
                    base_asset = asset_from_gate(base_asset_str)
                    quote_asset = asset_from_gate(quote_asset_str)
                except (UnknownAsset, KeyError, ValueError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key {msg}'
                    log.error(f'Could not read assets from Gate trade {raw_trade}: {msg}')
                    continue

                try:
                    is_buy = deserialize_trade_type_is_buy(side)
                    amount = deserialize_fval(raw_trade['amount'])
                    price = deserialize_price(raw_trade['price'])
                    spend, receive = get_swap_spend_receive(
                        is_buy=is_buy,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        amount=amount,
                        rate=price,
                    )
                except DeserializationError as e:
                    log.error(f'{e} when reading trade data for Gate trade {raw_trade}')
                    continue
                except KeyError as e:
                    log.error(
                        f'Failed to deserialize Gate trade {raw_trade} due to missing key {e}. '
                        'Skipping...',
                    )
                    continue

                fees: list[tuple[AssetAmount, str | None, None]] = []
                try:
                    if (fee_str := raw_trade.get('fee')) is not None and fee_str != '0':
                        fee_currency = asset_from_gate(raw_trade['fee_currency'])
                        fees.append((
                            AssetAmount(asset=fee_currency, amount=deserialize_fval(fee_str)),
                            None,
                            None,
                        ))
                    if (gt_fee_str := raw_trade.get('gt_fee')) is not None and gt_fee_str != '0':
                        gt_asset = asset_from_gate('GT')
                        fees.append((
                            AssetAmount(asset=gt_asset, amount=deserialize_fval(gt_fee_str)),
                            None,
                            None,
                        ))
                    if (point_fee_str := raw_trade.get('point_fee')) is not None and point_fee_str != '0':  # noqa: E501
                        point_asset = asset_from_gate('POINT')
                        fees.append((
                            AssetAmount(asset=point_asset, amount=deserialize_fval(point_fee_str)),
                            None,
                            None,
                        ))
                except (UnknownAsset, DeserializationError) as e:
                    log.error(f'Failed to process fees for Gate trade {raw_trade}: {e}')

                try:
                    timestamp = TimestampMS(deserialize_fval(raw_trade['create_time_ms']).to_int(exact=False))  # noqa: E501
                except (KeyError, ValueError) as e:
                    log.error(f'Failed to read timestamp for Gate trade {raw_trade}: {e}')
                    continue

                try:
                    events.extend(create_swap_events_multi_fee(
                        timestamp=timestamp,
                        location=self.location,
                        spend=spend,
                        receive=receive,
                        group_identifier=create_group_identifier_from_unique_id(
                            location=self.location,
                            unique_id=str(raw_trade['id']),
                        ),
                        fees=fees,
                        location_label=self.name,
                    ))
                except KeyError as e:
                    log.error(
                        f'Failed to deserialize Gate trade {raw_trade} due to missing key {e}. '
                        'Skipping...',
                    )

            if len(raw_data) < PAGINATION_LIMIT:
                break

            page += 1

        return events

    def _query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            query_for: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list[AssetMovement]:
        """Process deposits/withdrawals from Gate.

        The API returns results in descending order by default. We use from/to parameters
        (unix timestamps in seconds) to filter the time range.
        """
        log.debug(f'querying Gate online {query_for} with {start_ts=}-{end_ts=}')
        if query_for == HistoryEventType.DEPOSIT:
            endpoint = '/wallet/deposits'
            movement_subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.SPEND] = HistoryEventSubType.RECEIVE  # noqa: E501
        else:
            endpoint = '/wallet/withdrawals'
            movement_subtype = HistoryEventSubType.SPEND

        raw_data = []
        window_start = Timestamp(max(start_ts, GATE_MOVEMENTS_QUERY_START_TS))
        while window_start < end_ts:
            window_end = Timestamp(min(window_start + GATE_MAX_MOVEMENT_WINDOW, end_ts))
            offset = 0
            while True:
                try:
                    result = self._api_query(
                        path=endpoint,
                        options={
                            'from': window_start,
                            'to': window_end,
                            'limit': GATE_MOVEMENTS_PAGINATION_LIMIT,
                            'offset': offset,
                        },
                    )
                except RemoteError as e:
                    log.error(f'Failed to query Gate {query_for} due to {e!s}')
                    break

                if not isinstance(result, list):
                    log.error(f'Gate {query_for} response is not a list: {result}')
                    break

                raw_data.extend(result)
                if len(result) < GATE_MOVEMENTS_PAGINATION_LIMIT:
                    break

                offset += GATE_MOVEMENTS_PAGINATION_LIMIT

            window_start = window_end

        movements = []
        for movement in raw_data:
            try:
                timestamp = Timestamp(int(movement['timestamp']))
            except (KeyError, ValueError) as e:
                log.error(f'Failed to read timestamp for Gate movement {movement}: {e}')
                continue

            if not start_ts <= timestamp <= end_ts:
                continue

            try:
                asset = asset_from_gate(movement['currency'])
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='deposit/withdrawal',
                )
                continue
            except KeyError as e:
                log.error(f'Gate movement missing key {e}: {movement}')
                continue

            try:
                amount = deserialize_fval(movement['amount'])
                fee = None
                if query_for == HistoryEventType.WITHDRAWAL and 'fee' in movement:
                    fee = AssetAmount(
                        asset=asset,
                        amount=deserialize_fval(movement['fee']),
                    )

                movements.extend(create_asset_movement_with_fee(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=self.location,
                    location_label=self.name,
                    event_subtype=movement_subtype,
                    asset=asset,
                    amount=amount,
                    fee=fee,
                    unique_id=str(movement['id']),
                    extra_data=maybe_set_transaction_extra_data(
                        address=deserialize_asset_movement_address(
                            mapping=movement,
                            key='address',
                            asset=asset,
                        ),
                        transaction_id=get_key_if_has_val(movement, 'txid'),
                    ),
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key {msg}'
                log.error(f'{msg} when reading Gate movement {movement}. Skipping...')
                continue

        return movements

    @protect_with_lock()
    def query_history_events(self) -> None:
        """Queries Gate events in 30-day chunks and commits each chunk.

        Gate deposit/withdrawal endpoints reject ranges longer than 30 days. Committing each
        chunk avoids re-querying already processed chunks if a later chunk fails.
        """
        self.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_STARTED)
        db = DBHistoryEvents(self.db)
        location_string = f'{self.location!s}_history_events_{self.name}'
        with self.db.conn.read_ctx() as cursor:
            ranges_to_query = (ranges := DBQueryRanges(self.db)).get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=GATE_MOVEMENTS_QUERY_START_TS,
                end_ts=ts_now(),
            )

        for query_start_ts, query_end_ts in ranges_to_query:
            chunk_start = query_start_ts
            while chunk_start < query_end_ts:
                chunk_end = Timestamp(min(chunk_start + GATE_MAX_MOVEMENT_WINDOW, query_end_ts))
                log.debug(
                    f'Querying Gate history events chunk for {self.name} with '
                    f'{chunk_start=}, {chunk_end=}',
                )
                self.send_history_events_status_msg(
                    step=HistoryEventsStep.QUERYING_EVENTS_STATUS_UPDATE,
                    period=[chunk_start, chunk_end],
                )
                new_events, actual_end_ts = self.query_online_history_events(
                    start_ts=chunk_start,
                    end_ts=chunk_end,
                )
                with self.db.user_write() as write_cursor:
                    if len(new_events) != 0:
                        db.add_history_events(write_cursor=write_cursor, history=new_events)
                    ranges.update_used_query_range(
                        write_cursor=write_cursor,
                        location_string=location_string,
                        queried_ranges=[(chunk_start, actual_end_ts)],
                    )
                log.debug(
                    f'Finished querying Gate history events chunk for {self.name} with '
                    f'{chunk_start=}, {actual_end_ts=}, events_num={len(new_events)}',
                )

                if actual_end_ts != chunk_end:
                    log.error(
                        f'Failed to query all {self.name} history events between {chunk_start} '
                        f'and {chunk_end}. Last successfully queried timestamp: {actual_end_ts}',
                    )
                    self.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_FINISHED)
                    return

                chunk_start = chunk_end

        self.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_FINISHED)

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple[Sequence[HistoryBaseEntry], Timestamp]:
        """Query deposits, withdrawals, and trades from Gate."""
        events: list[AssetMovement | SwapEvent] = []
        movement_tasks = [
            spawn(
                self._query_deposits_withdrawals,
                start_ts=start_ts,
                end_ts=end_ts,
                query_for=event_type,
            ) for event_type in (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL)
        ]
        wait(movement_tasks)
        for task in movement_tasks:
            events.extend(result_of(task))

        events.extend(self._query_trades(start_ts=start_ts, end_ts=end_ts))
        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for Gate
