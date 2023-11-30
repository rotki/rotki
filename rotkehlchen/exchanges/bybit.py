
from collections import defaultdict
from enum import auto
import hashlib
import hmac
import json
import logging
from multiprocessing.managers import RemoteError
import operator
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode
import gevent

import requests
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.api.websockets.typedefs import HistoryEventsQueryType, HistoryEventsStep, WSMessageType
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bybit
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import asset_movement_from_history_events
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_asset_amount_force_positive, deserialize_fee, deserialize_fval, deserialize_timestamp, deserialize_timestamp_from_intms
from rotkehlchen.types import ApiKey, ApiSecret, AssetMovementCategory, ExchangeAuthCredentials, Location, Timestamp
from rotkehlchen.utils.misc import ts_now, ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

PAGINATION_LIMIT: Final = 48
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)



def bybit_ledger_entry_type_to_ours(bybit_type: str) -> tuple[HistoryEventType, HistoryEventSubType]:
    
    event_type = HistoryEventType.INFORMATIONAL  # returned for kraken's unknown events
    event_subtype = HistoryEventSubType.NONE  # may be further edited down out of this function

    if bybit_type == 'TRANSFER_IN':
        event_type = HistoryEventType.DEPOSIT
        event_subtype = HistoryEventSubType.DEPOSIT_ASSET
    elif bybit_type == 'TRANSFER_OUT':
        event_type = HistoryEventType.WITHDRAWAL
        event_subtype = HistoryEventSubType.REMOVE_ASSET
    elif bybit_type == 'TRADE':
        event_type = HistoryEventType.TRADE
    elif bybit_type == 'AIRDROP':
        event_type = HistoryEventType.RECEIVE
        event_subtype = HistoryEventSubType.AIRDROP
    elif bybit_type == 'FEE_REFUND':
        event_type = HistoryEventType.RECEIVE
        event_subtype = HistoryEventSubType.REFUND
    elif bybit_type == 'BONUS':
        event_type = HistoryEventType.RECEIVE
    elif bybit_type == 'AUTO_DEDUCTION':
        event_type = HistoryEventType.ADJUSTMENT

    return event_type, event_subtype


class Bybit(ExchangeInterface):
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
            location=Location.BYBIT,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.uri = 'https://api.bybit.com/v5'
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({'Content-Type': 'application/json', 'X-BAPI-SIGN-TYPE': '2'})
        self.recv_window = str(5000)
        self.authenticated_methods = {
            'account/wallet-balance',
            'account/transaction-log',
        }
        self.history_events_db = DBHistoryEvents(self.db)

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed is True:
            self.session.headers.update({'X-BAPI-API-KEY': self.api_key})

        return changed
    
    def _generate_signature(self, param_str: str) -> str:
        hash = hmac.new(
            key=self.secret,
            msg=param_str.encode('utf-8'),
            digestmod=hashlib.sha256,
        )
        return hash.hexdigest()
        
    def _deserialize_bybit_event_group(self, related_entries: list[dict[str, Any]]) -> list[HistoryEvent]:
        current_fee_index = len(related_entries)
        events = []
        for idx, raw_event in enumerate(related_entries):
            event_identifier = f'{self.location}_{raw_event["id"]}'
            timestamp = deserialize_timestamp_from_intms(int(raw_event['transactionTime']))
            event_type, event_subtype = bybit_ledger_entry_type_to_ours(raw_event['type'])
            asset = asset_from_bybit(raw_event['currency'])
            # Change = cashFlow + funding - fee
            amount = deserialize_asset_amount(raw_event['change'])
            fee_amount = deserialize_asset_amount(raw_event['fee'])

            notes = None
            if event_type == HistoryEventType.TRADE:
                event_subtype = HistoryEventSubType.SPEND if amount < ZERO else HistoryEventSubType.RECEIVE  # noqa: E501

            events.append(HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=idx,
                timestamp=timestamp,
                location=Location.BYBIT,
                location_label=self.name,
                asset=asset,
                balance=Balance(amount=amount, usd_value=ZERO),
                notes=notes,
                event_type=event_type,
                event_subtype=event_subtype,
            ))
            if fee_amount != ZERO:
                fee_event_type = event_type
                fee_event_subtype = HistoryEventSubType.FEE
                # if fee is positive is a rebate
                if fee_amount > ZERO:
                    fee_event_type = HistoryEventType.ADJUSTMENT
                    fee_event_subtype = HistoryEventSubType.RECEIVE
                else:
                    fee_amount = abs(fee_amount)

                events.append(HistoryEvent(
                    event_identifier=event_identifier,
                    sequence_index=current_fee_index,
                    timestamp=timestamp,
                    location=Location.BYBIT,
                    location_label=self.name,
                    asset=asset,
                    balance=Balance(amount=fee_amount, usd_value=ZERO),
                    notes=notes,
                    event_type=fee_event_type,
                    event_subtype=fee_event_subtype,
                ))
                current_fee_index += 1

        return events

    def process_bybit_raw_events(
            self,
            events: list[dict[str, Any]],
            events_source: str,
    ) -> list[HistoryEvent]:
        raw_events_grouped = defaultdict(list)
        for raw_event in events:
            raw_events_grouped[raw_event['id']].append(raw_event)

        new_events = []
        for raw_events in raw_events_grouped.values():
            group_events = self._deserialize_bybit_event_group(related_entries=raw_events)
            new_events.extend(group_events)
        
        if len(new_events) != 0:
            with self.db.user_write() as write_cursor:
                try:  # duplicates should be handled due to INSERT OR IGNORE and UNIQUE(event_identifier, sequence_index)  # noqa: E501
                    self.history_events_db.add_history_events(write_cursor=write_cursor, history=new_events)  # noqa: E501
                except InputError as e:  # not catching IntegrityError. event asset is resolved
                    self.msg_aggregator.add_error(
                        f'Failed to save bybit events from {events_source} in database. {e!s}',
                    )

        return new_events

    def _api_query(
            self,
            verb: Literal['get', 'post'],
            path: Literal[
                'account/wallet-balance',
                'account/transaction-log',
            ],
            options: dict | None = None,
    ) -> dict:
        """
        Query bybit endpoints.
        May raise:
        - RemoteError
        """
        url = f'{self.uri}/{path}'
        timeout = CachedSettings().get_timeout_tuple()
        tries = CachedSettings().get_query_retry_limit()
        requires_auth = path in self.authenticated_methods

        while True:
            log.debug('Bybit API Query', verb=verb, url=url, options=options)
            if requires_auth:
                timestamp = ts_now_in_ms()
                # the order in this string is defined by the api
                param_str = str(timestamp) + self.api_key + self.recv_window
                if verb == 'get' and options is not None:
                    param_str += '&'.join(  # params need to be sorted to be correctly validated
                        [
                            str(k) + '=' + str(v)
                            for k, v in sorted(options.items())
                            if v is not None
                        ]
                    )
                elif verb == 'post' and options is not None:
                    param_str += json.dumps(options)

                signature = self._generate_signature(param_str=param_str)
                self.session.headers = {
                    'Content-Type': 'application/json',
                    'X-BAPI-SIGN-TYPE': '2',
                    'X-BAPI-RECV-WINDOW': self.recv_window,
                    'X-BAPI-API-KEY': self.api_key,
                    'X-BAPI-TIMESTAMP': str(timestamp),
                    'X-BAPI-SIGN': signature,
                }
            else:
                self.session.headers = {'Content-Type': 'application/json', 'X-BAPI-SIGN-TYPE': '2'}  # noqa: E501

            try:
                response = self.session.request(
                    method=verb,
                    url=url,
                    params=options if verb == 'get' else None,
                    data=options if verb == 'post' else None,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Bybit API request failed due to {e}') from e

            if response.status_code not in {200, 429}:
                raise RemoteError(
                    f'Bybit api request for {response.url} failed with HTTP status '
                    f'code {response.status_code} and response {response.text}',
                )

            if response.status_code == 429:
                if tries >= 1:
                    backoff_seconds = 10 / tries
                    log.debug(
                        f'Got a 429 from Bybit. Backing off for {backoff_seconds}')
                    gevent.sleep(backoff_seconds)
                    tries -= 1
                    continue

                # else
                raise RemoteError(
                    f'Bybit api request for {response.url} failed with HTTP '
                    f'status code {response.status_code} and response {response.text}',
                )

            break  # else all good, we can break off the retry loop

        try:
            json_ret = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError('Bybit returned invalid JSON response') from e
        if 'result' not in json_ret:
            raise RemoteError(f'Remote response is missing expected field result: {json_ret}')
        print(json_ret)
        return json_ret['result']

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bybit API key is good for usage in rotki"""
        try:
            self._api_query(verb='post', method_type='Private', path='GetAccounts')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''
        
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)

        try:
            response = self._api_query(verb='get', path='account/wallet-balance', options={'accountType': 'UNIFIED'})
        except RemoteError as e:
            msg = f'Bybit request failed. Could not reach the exchange due to {e!s}'
            log.error(msg)
            return None, msg

        log.debug(f'IndependentReserve account response: {response}')
        for account in response['list']:
            for coin_data in account['coin']:
                try:
                    asset = asset_from_bybit(coin_data['coin'])
                    amount = deserialize_fval(coin_data['walletBalance'], name=f'Bybit wallet balance for {asset}', location='bybit')
                    usd_value = deserialize_fval(coin_data['usdValue'], name=f'Bybit usd value for {asset}', location='bybit')  # we don't need to calculate it since it is provided by bybit  # noqa: E501
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found Bybit balance result with unknown asset '
                        f'{e.identifier}. Ignoring it.',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    return None, f'Error processing Bybit balance entry {coin_data}. {msg}'

                assets_balance[asset] += Balance(amount=amount, usd_value=usd_value)

        return assets_balance, ''
    
    @protect_with_lock()
    def _query_ledger(
            self,
            cursor: DBCursor,
            start_ts: Timestamp,
            end_ts: Timestamp,
            notify_events: bool = False,
    ) -> None:
        """Query and process the bybit ledger"""
        ranges = DBQueryRanges(self.db)
        location_string = f'{self.location}_history_events_{self.name}'
        with self.db.conn.read_ctx() as cursor:
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

            for query_start_ts, query_end_ts in ranges_to_query:
                # If we have a time frame we have not asked the exchange for trades then
                # go ahead and do that now
                log.debug(
                    f'Querying online bybit history for {self.name} between '
                    f'{query_start_ts} and {query_end_ts}',
                )
                if notify_events is True:
                    self.msg_aggregator.add_message(
                        message_type=WSMessageType.HISTORY_EVENTS_STATUS,
                        data={
                            'status': str(HistoryEventsStep.QUERYING_EVENTS_STATUS_UPDATE),
                            'location': str(self.location),
                            'event_type': str(HistoryEventsQueryType.HISTORY_QUERY),
                            'name': self.name,
                            'period': [query_start_ts, query_end_ts],
                        },
                    )

                options = {
                    'accountType': 'UNIFIED',
                    'endTime': str(ts_sec_to_ms(query_end_ts)),
                    'limit': PAGINATION_LIMIT,
                    'startTime': str(ts_sec_to_ms(query_end_ts - DAY_IN_SECONDS*4)),
                }
                events = []
                while True:
                    query_result = self._api_query(
                        verb='get',
                        path='account/transaction-log',
                        options=options,
                    )
                    if len(query_result) == 0:
                        log.info(f'Got no events from bybit ledger with the {options} filter')
                        break

                    next_page_cursor = query_result['nextPageCursor']
                    events.extend(query_result['list'])

                    if len(events) < PAGINATION_LIMIT:
                        break

                    options['cursor'] = next_page_cursor

                # Process the collected events
                new_events = self.process_bybit_raw_events(
                    events=events,
                    events_source=f'query range {query_start_ts}-{query_end_ts}'
                )
                if len(new_events) != 0:
                    with self.db.user_write() as write_cursor:
                        ranges.update_used_query_range(
                            write_cursor=write_cursor,
                            location_string=location_string,
                            queried_ranges=[(query_start_ts, query_end_ts)],
                        )

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for bybit

    def query_online_income_loss_expense(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list['HistoryEvent']:
        return []  # noop for bybit
    
    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        with self.db.conn.read_ctx() as cursor:
            self._query_ledger(cursor, start_ts=start_ts, end_ts=end_ts)
            filter_query = HistoryEventFilterQuery.make(
                from_ts=Timestamp(start_ts),
                to_ts=Timestamp(end_ts),
                event_types=[
                    HistoryEventType.DEPOSIT,
                    HistoryEventType.WITHDRAWAL,
                ],
                location=Location.BYBIT,
                location_labels=[self.name],
                entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
            )
            events = self.history_events_db.get_history_events(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=True,
            )

        log.debug('Bybit deposit/withdrawals query result', num_results=len(events))
        movements = asset_movement_from_history_events(
            events=events,
            location=Location.BYBIT,
            msg_aggregator=self.msg_aggregator,
        )
        return movements

    def query_history_events(self) -> None:
        self.msg_aggregator.add_message(
            message_type=WSMessageType.HISTORY_EVENTS_STATUS,
            data={
                'status': str(HistoryEventsStep.QUERYING_EVENTS_STARTED),
                'location': str(self.location),
                'event_type': str(HistoryEventsQueryType.HISTORY_QUERY),
                'name': self.name,
            },
        )
        with self.db.conn.read_ctx() as cursor:
            # We give the full range but internally it queries only for the missing time ranges
            self._query_ledger(
                cursor=cursor,
                start_ts=Timestamp(0),
                end_ts=ts_now(),
                notify_events=True,
            )
        self.msg_aggregator.add_message(
            message_type=WSMessageType.HISTORY_EVENTS_STATUS,
            data={
                'status': str(HistoryEventsStep.QUERYING_EVENTS_FINISHED),
                'location': str(self.location),
                'event_type': str(HistoryEventsQueryType.HISTORY_QUERY),
                'name': self.name,
            },
        )
