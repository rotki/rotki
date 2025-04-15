# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/clikraken
import base64
import hashlib
import hmac
import itertools
import json
import logging
import operator
import time
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import gevent
import requests
from requests import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import KRAKEN_API_VERSION, KRAKEN_BASE_URL, ZERO
from rotkehlchen.constants.assets import A_ETH2, A_KFEE, A_USD
from rotkehlchen.db.constants import KRAKEN_ACCOUNT_TYPE_KEY
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import (
    ExchangeInterface,
    ExchangeQueryBalances,
    ExchangeWithExtras,
)
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    HistoryEvent,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fval,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import pairwise, ts_ms_to_sec, ts_now
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KRAKEN_QUERY_TRIES = 8
KRAKEN_BACKOFF_DIVIDEND = 15
MAX_CALL_COUNTER_INCREASE = 2  # Trades and Ledger produce the max increase


def kraken_ledger_entry_type_to_ours(value: str) -> tuple[HistoryEventType, HistoryEventSubType]:
    """Turns a kraken ledger entry to our history event type, subtype combination

    Though they are very similar to our current event types we keep this mapping function
    since there is some minor differences and if we ever want to change our types we
    can do so without breaking kraken.

    Docs: https://support.kraken.com/hc/en-us/articles/360001169383-How-to-interpret-Ledger-history-fields

    Returns Informational type for any kraken event that we don't know how to process
    """
    event_type = HistoryEventType.INFORMATIONAL  # returned for kraken's unknown events
    event_subtype = HistoryEventSubType.NONE  # may be further edited down out of this function
    if value == 'trade':
        event_type = HistoryEventType.TRADE
    if value == 'staking':
        event_type = HistoryEventType.STAKING
    if value == 'deposit':
        event_type = HistoryEventType.DEPOSIT
    if value == 'withdrawal':
        event_type = HistoryEventType.WITHDRAWAL
    if value == 'spend':
        event_type = HistoryEventType.SPEND
    if value == 'receive':
        event_type = HistoryEventType.RECEIVE
    if value == 'transfer':
        event_type = HistoryEventType.TRANSFER
    if value == 'adjustment':
        event_type = HistoryEventType.ADJUSTMENT
    if value == 'invite bonus':
        event_type = HistoryEventType.RECEIVE
        event_subtype = HistoryEventSubType.REWARD

    # we ignore margin, rollover, settled since they are for margin trades
    return event_type, event_subtype


def _check_and_get_response(response: Response, method: str) -> str | dict:
    """Checks the kraken response and if it's successful returns the result.

    If there is recoverable error a string is returned explaining the error
    May raise:
    - RemoteError if there is an unrecoverable/unexpected remote error
    """
    if response.status_code in {520, 525, 504}:
        log.debug(f'Kraken returned status code {response.status_code}')
        return 'Usual kraken 5xx shenanigans'
    if response.status_code != 200:
        raise RemoteError(
            f'Kraken API request {response.url} for {method} failed with HTTP status '
            f'code: {response.status_code}')

    try:
        decoded_json = jsonloads_dict(response.text)
    except json.decoder.JSONDecodeError as e:
        raise RemoteError(f'Invalid JSON in Kraken response. {e}') from e

    error = decoded_json.get('error', None)
    if error:
        if isinstance(error, list) and len(error) != 0:
            error = error[0]

        if 'Rate limit exceeded' in error:
            log.debug(f'Kraken: Got rate limit exceeded error: {error}')
            return 'Rate limited exceeded'

        # else
        raise RemoteError(error)

    result = decoded_json.get('result', None)
    if result is None:
        if method == 'Balance':
            return {}

        raise RemoteError(f'Missing result in kraken response for {method}')

    return result


class KrakenAccountType(SerializableEnumNameMixin):
    STARTER = 0
    INTERMEDIATE = 1
    PRO = 2


DEFAULT_KRAKEN_ACCOUNT_TYPE = KrakenAccountType.STARTER


class Kraken(ExchangeInterface, ExchangeWithExtras):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            kraken_account_type: KrakenAccountType | None = None,
    ):
        super().__init__(
            name=name,
            location=Location.KRAKEN,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.session.headers.update({'API-Key': self.api_key})
        self.set_account_type(kraken_account_type)
        self.call_counter = 0
        self.last_query_ts = 0
        self.history_events_db = DBHistoryEvents(self.db)

    def set_account_type(self, account_type: KrakenAccountType | None) -> None:
        if account_type is None:
            account_type = DEFAULT_KRAKEN_ACCOUNT_TYPE

        self.account_type = account_type
        if self.account_type == KrakenAccountType.STARTER:
            self.call_limit = 15
            self.reduction_every_secs = 3
        elif self.account_type == KrakenAccountType.INTERMEDIATE:
            self.call_limit = 20
            self.reduction_every_secs = 2
        else:  # Pro
            self.call_limit = 20
            self.reduction_every_secs = 1

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'API-Key': self.api_key})

        return changed

    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        account_type = extras.get(KRAKEN_ACCOUNT_TYPE_KEY)
        if account_type is None:
            return False, 'No account type provided'

        # now we can update the account type
        self.set_account_type(account_type)
        return True, ''

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Kraken API Key is good for usage in Rotkehlchen

        Makes sure that the following permission are given to the key:
        - Ability to query funds
        - Ability to query open/closed trades
        - Ability to query ledgers
        """
        valid, msg = self._validate_single_api_key_action('Balance')
        if not valid:
            return False, msg
        valid, msg = self._validate_single_api_key_action(
            method_str='TradesHistory',
            req={'start': 0, 'end': 0},
        )
        if not valid:
            return False, msg
        valid, msg = self._validate_single_api_key_action(
            method_str='Ledgers',
            req={'start': 0, 'end': 0, 'type': 'deposit'},
        )
        if not valid:
            return False, msg
        return True, ''

    def _validate_single_api_key_action(
            self,
            method_str: Literal['Balance', 'TradesHistory', 'Ledgers'],
            req: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        try:
            self.api_query(method_str, req)
        except (RemoteError, ValueError) as e:
            error = str(e)
            if 'Incorrect padding' in error:
                return False, 'Provided API Key or secret is invalid'
            if 'EAPI:Invalid key' in error:
                return False, 'Provided API Key is invalid'
            if 'EGeneral:Permission denied' in error:
                msg = (
                    'Provided API Key does not have appropriate permissions. Make '
                    'sure that the "Query Funds", "Query Open/Closed Order and Trades"'
                    'and "Query Ledger Entries" actions are allowed for your Kraken API Key.'
                )
                return False, msg

            # else
            log.error(f'Kraken API key validation error: {e!s}')
            msg = (
                'Unknown error at Kraken API key validation. Perhaps API '
                'Key/Secret combination invalid?'
            )
            return False, msg
        return True, ''

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _manage_call_counter(self, method: str) -> None:
        self.last_query_ts = ts_now()
        if method in {'Ledgers', 'TradesHistory'}:
            self.call_counter += 2
        else:
            self.call_counter += 1

    def api_query(self, method: str, req: dict | None = None) -> dict:
        tries = KRAKEN_QUERY_TRIES
        while tries > 0:
            if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                # If we are close to the limit, check how much our call counter reduced
                # https://www.kraken.com/features/api#api-call-rate-limit
                secs_since_last_call = ts_now() - self.last_query_ts
                self.call_counter = max(
                    0,
                    self.call_counter - int(secs_since_last_call / self.reduction_every_secs),
                )
                # If still at limit, sleep for an amount big enough for smallest tier reduction
                if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                    backoff_in_seconds = self.reduction_every_secs * 2
                    log.debug(
                        f'Doing a Kraken API call would now exceed our call counter limit. '
                        f'Backing off for {backoff_in_seconds} seconds',
                        call_counter=self.call_counter,
                    )
                    tries -= 1
                    gevent.sleep(backoff_in_seconds)
                    continue

            log.debug(
                'Kraken API query',
                method=method,
                data=req,
                call_counter=self.call_counter,
            )
            result = self._query_private(method, req)
            if isinstance(result, str):
                # Got a recoverable error
                backoff_in_seconds = int(KRAKEN_BACKOFF_DIVIDEND / tries)
                log.debug(
                    f'Got recoverable error {result} in a Kraken query of {method}. Will backoff '
                    f'for {backoff_in_seconds} seconds',
                )
                tries -= 1
                gevent.sleep(backoff_in_seconds)
                continue

            # else success
            return result

        raise RemoteError(
            f'After {KRAKEN_QUERY_TRIES} kraken queries for {method} could still not be completed',
        )

    def _query_private(self, method: str, req: dict | None = None) -> dict | str:
        """API queries that require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})

        """
        if req is None:
            req = {}

        urlpath = '/' + KRAKEN_API_VERSION + '/private/' + method
        req['nonce'] = int(1000 * time.time())
        post_data = urlencode(req)
        # any unicode strings must be turned to bytes
        hashable = (str(req['nonce']) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            base64.b64decode(self.secret),
            message,
            hashlib.sha512,
        )
        self.session.headers.update({
            'API-Sign': base64.b64encode(signature.digest()),
        })
        try:
            response = self.session.post(
                KRAKEN_BASE_URL + urlpath,
                data=post_data.encode(),
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {e!s}') from e
        self._manage_call_counter(method)

        return _check_and_get_response(response, method)

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            kraken_balances = self.api_query('Balance', req={})
        except RemoteError as e:
            if "Missing key: 'result'" in str(e):
                # handle https://github.com/rotki/rotki/issues/946
                kraken_balances = {}
            else:
                msg = (
                    'Kraken API request failed. Could not reach kraken due '
                    f'to {e}'
                )
                log.error(msg)
                return None, msg

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for kraken_name, amount_ in kraken_balances.items():
            try:
                amount = deserialize_asset_amount(amount_)
                if amount == ZERO:
                    continue

                our_asset = asset_from_kraken(kraken_name)
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except DeserializationError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    f'Error processing kraken balance for {kraken_name}. Check logs '
                    f'for details. Ignoring it.',
                )
                log.error(
                    'Error processing kraken balance',
                    kraken_name=kraken_name,
                    amount=amount_,
                    error=msg,
                )
                continue

            balance = Balance(amount=amount)
            if our_asset.identifier != 'KFEE':
                # There is no price value for KFEE
                try:
                    usd_price = Inquirer.find_usd_price(our_asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing kraken balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                balance.usd_value = balance.amount * usd_price

            assets_balance[our_asset] += balance
            log.debug(
                'kraken balance query result',
                currency=our_asset,
                amount=balance.amount,
                usd_value=balance.usd_value,
            )

        return dict(assets_balance), ''

    def query_until_finished(
            self,
            endpoint: Literal['Ledgers'],
            keyname: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            extra_dict: dict | None = None,
    ) -> tuple[list, bool]:
        """ Abstracting away the functionality of querying a kraken endpoint where
        you need to check the 'count' of the returned results and provide sufficient
        calls with enough offset to gather all the data of your query.
        """
        result: list = []

        with_errors = False
        log.debug(
            f'Querying Kraken {endpoint} from {start_ts} to '
            f'{end_ts} with extra_dict {extra_dict}',
        )
        response = self._query_endpoint_for_period(
            endpoint=endpoint,
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict=extra_dict,
        )
        count = response['count']
        offset = len(response[keyname])
        result.extend(response[keyname].values())

        log.debug(f'Kraken {endpoint} Query Response with count:{count}')

        while offset < count:
            log.debug(
                f'Querying Kraken {endpoint} from {start_ts} to {end_ts} '
                f'with offset {offset} and extra_dict {extra_dict}',
            )
            try:
                response = self._query_endpoint_for_period(
                    endpoint=endpoint,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    offset=offset,
                    extra_dict=extra_dict,
                )
            except RemoteError as e:
                with_errors = True
                log.error(
                    f'One of krakens queries when querying endpoint for period failed '
                    f'with {e!s}. Returning only results we have.',
                )
                break

            if count != response['count']:
                log.error(
                    f'Kraken unexpected response while querying endpoint for period. '
                    f'Original count was {count} and response returned {response["count"]}',
                )
                with_errors = True
                break

            response_length = len(response[keyname])
            offset += response_length
            if response_length == 0 and offset != count:
                # If we have provided specific filtering then this is a known
                # issue documented below, so skip the warning logging
                # https://github.com/rotki/rotki/issues/116
                if extra_dict:
                    break
                # it is possible that kraken misbehaves and either does not
                # send us enough results or thinks it has more than it really does
                log.warning(
                    f'Missing {count - offset} results when querying kraken '
                    f'endpoint {endpoint}',
                )
                with_errors = True
                break

            result.extend(response[keyname].values())

        return result, with_errors

    def _query_endpoint_for_period(
            self,
            endpoint: Literal['Ledgers'],
            start_ts: Timestamp,
            end_ts: Timestamp,
            offset: int | None = None,
            extra_dict: dict | None = None,
    ) -> dict:
        request: dict[str, Timestamp | int] = {}
        request['start'] = start_ts
        request['end'] = end_ts
        if offset is not None:
            request['ofs'] = offset
        if extra_dict is not None:
            request.update(extra_dict)
        return self.api_query(endpoint, request)

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for kraken

    def process_kraken_events_for_trade(
            self,
            trade_parts: list[HistoryEvent],
    ) -> list[SwapEvent]:
        """Processes events from trade parts to a list of SwapEvents. If it's an adjustment
        adds it to a separate list"""
        event_id = trade_parts[0].event_identifier
        is_spend_receive = False
        trade_assets = []
        spend_part, receive_part, fee_part, kfee_part = None, None, None, None

        for trade_part in trade_parts:
            if trade_part.event_type == HistoryEventType.RECEIVE:
                is_spend_receive = True
                receive_part = trade_part
            elif trade_part.event_type == HistoryEventType.SPEND:
                if trade_part.event_subtype == HistoryEventSubType.FEE:
                    fee_part = trade_part
                else:
                    is_spend_receive = True
                    spend_part = trade_part
            elif trade_part.event_type == HistoryEventType.TRADE:
                if trade_part.event_subtype == HistoryEventSubType.FEE:
                    fee_part = trade_part
                elif trade_part.event_subtype == HistoryEventSubType.SPEND:
                    spend_part = trade_part
                elif trade_part.asset == A_KFEE:
                    kfee_part = trade_part
                else:
                    receive_part = trade_part

            if (
                trade_part.amount != ZERO and
                trade_part.event_subtype != HistoryEventSubType.FEE
            ):
                trade_assets.append(trade_part.asset)

        if is_spend_receive and len(trade_parts) < 2:
            log.warning(
                f'Found kraken spend/receive events {event_id} with '
                f'less than 2 parts. {trade_parts}',
            )
            self.msg_aggregator.add_warning(
                f'Found kraken spend/receive events {event_id} with '
                f'less than 2 parts. Skipping...',
            )
            return []

        exchange_uuid = (
            str(event_id) +
            str(timestamp := trade_parts[0].timestamp)
        )
        if len(trade_assets) != 2:
            # This can happen some times (for lefteris 5 times since start of kraken usage)
            # when the other part of a trade is so small it's 0. So it's either a
            # receive event with no counterpart or a spend event with no counterpart.
            # This happens for really really small amounts. So we add rate 0 trades
            if spend_part is not None:
                spend_asset = spend_part.asset
                spend_amount = spend_part.amount
                receive_asset = A_USD  # whatever
                receive_amount = ZERO
            elif receive_part is not None:
                spend_asset = A_USD  # whatever
                spend_amount = ZERO
                receive_asset = receive_part.asset
                receive_amount = receive_part.amount
            else:
                log.warning(f'Found historic trade entries with no counterpart {trade_parts}')
                return []

            return create_swap_events(
                timestamp=timestamp,
                location=Location.KRAKEN,
                spend_asset=spend_asset,
                spend_amount=spend_amount,
                receive_asset=receive_asset,
                receive_amount=receive_amount,
                unique_id=exchange_uuid,
            )

        if spend_part is None or receive_part is None:
            log.error(
                f"Failed to process {event_id}. Couldn't find "
                f'spend/receive parts {trade_parts}',
            )
            self.msg_aggregator.add_error(
                f'Failed to read trades for event {event_id}. '
                f'More details are available at the logs',
            )
            return []

        # If kfee was found we use it as the fee for the trade
        if kfee_part is not None and fee_part is None:
            fee = kfee_part.amount
            fee_asset = A_KFEE
        else:
            fee = fee_part.amount if fee_part is not None else ZERO
            fee_asset = fee_part.asset if fee_part is not None else A_USD

        return create_swap_events(
            timestamp=timestamp,
            location=Location.KRAKEN,
            spend_asset=spend_part.asset,
            spend_amount=spend_part.amount,
            receive_asset=receive_part.asset,
            receive_amount=receive_part.amount,
            fee_asset=fee_asset,
            fee_amount=fee,
            unique_id=exchange_uuid,
        )

    def process_kraken_trades(
            self,
            trade_events: list[HistoryEvent],
            adjustments: list[HistoryEvent],
    ) -> tuple[list[SwapEvent | HistoryEvent], Timestamp]:
        """Process history events converting them into SwapEvents.
        `trade_events` contains Trade, Receive, and Spend events.
        `adjustments` contains Adjustment events.

        A pair of receive and spend events can be a trade and kraken uses this kind of event
        for instant trades and trades made from the phone app. What we do in order to verify
        that it is a trade is to check if we can find a pair with the same event id.

        Also in some rare occasions Kraken may forcibly adjust something for you.
        Example would be delisting of DAO token and forcible exchange to ETH.

        Returns:
        - The list of SwapEvents and any adjustment events that were not converted.
        - The biggest timestamp of all the trades processed

        May raise:
        - RemoteError if the pairs couldn't be correctly queried
        """
        swap_events = []
        max_ts = 0
        get_attr = operator.attrgetter('event_identifier')
        # Create a list of lists where each sublist has the events for the same event identifier
        grouped_events = [list(g) for k, g in itertools.groupby(sorted(trade_events, key=get_attr), get_attr)]  # noqa: E501
        for trade_parts in grouped_events:
            if len(events := self.process_kraken_events_for_trade(trade_parts)) == 0:
                continue

            swap_events.extend(events)
            max_ts = max(max_ts, ts_ms_to_sec(events[0].timestamp))

        adjustments.sort(key=lambda x: x.timestamp)
        if len(adjustments) % 2 == 0:
            for a1, a2 in pairwise(adjustments):
                if a1.event_subtype is None or a2.event_subtype is None:
                    log.warning(
                        f'Found two kraken adjustment entries without a subtype: {a1} {a2}',
                    )
                    continue

                if a1.event_subtype == HistoryEventSubType.SPEND and a2.event_subtype == HistoryEventSubType.RECEIVE:  # noqa: E501
                    spend_event = a1
                    receive_event = a2
                elif a2.event_subtype == HistoryEventSubType.SPEND and a2.event_subtype == HistoryEventSubType.RECEIVE:  # noqa: E501
                    spend_event = a2
                    receive_event = a1
                else:
                    log.warning(
                        f'Found two kraken adjustment with unmatching subtype {a1} {a2}',
                    )
                    continue

                swap_events.extend(create_swap_events(
                    timestamp=a1.timestamp,
                    location=Location.KRAKEN,
                    spend_asset=spend_event.asset,
                    spend_amount=spend_event.amount,
                    receive_asset=receive_event.asset,
                    receive_amount=receive_event.amount,
                    unique_id='adjustment' + a1.event_identifier + a2.event_identifier,
                ))
                # Remove these adjustments since they are now represented by SwapEvents
                adjustments.remove(a1)
                adjustments.remove(a2)

        else:
            log.warning(
                f'Got odd number of kraken adjustment historic entries. '
                f'Skipping reading them. {adjustments}',
            )

        return swap_events + adjustments, Timestamp(max_ts)

    def process_kraken_raw_events(
            self,
            events: list[dict[str, Any]],
            events_source: str,
            save_skipped_events: bool,
    ) -> tuple[list[HistoryEvent | AssetMovement], set[str]]:
        """Run through a list of raw kraken events with different refids and process them.

        Returns a list of the newly created rotki events and a set of all processed refids
        """
        # Group related events
        raw_events_grouped = defaultdict(list)
        processed_refids = set()
        for raw_event in events:
            raw_events_grouped[raw_event['refid']].append(raw_event)

        new_events = []
        for raw_events in raw_events_grouped.values():
            try:
                events = sorted(
                    raw_events,
                    key=lambda x: deserialize_fval(x['time'], 'time', 'kraken ledgers') * 1000,
                )
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Failed to read timestamp in kraken event group '
                    f'due to {e!s}. For more information read the logs. Skipping event',
                )
                log.error(f'Failed to read timestamp for {raw_events}')
                continue

            group_events, skipped, found_unknown_event = self.history_event_from_kraken(
                events=events,
                save_skipped_events=save_skipped_events,
            )
            if found_unknown_event:
                for event in group_events:
                    event.event_type = HistoryEventType.INFORMATIONAL
            if not skipped:
                processed_refids.add(events[0]['refid'])
            new_events.extend(group_events)

        return new_events, processed_refids

    @protect_with_lock()
    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Query Kraken's ledger to retrieve events and transform them to our
        internal representation of history events.

        May raise:
        - RemoteError if request to kraken fails for whatever reason

        Returns a tuple containing a list of events found
        and the last successfully queried timestamp.
        """
        log.debug(f'Querying kraken ledger entries from {start_ts} to {end_ts}')
        try:
            response, with_errors = self.query_until_finished(
                endpoint='Ledgers',
                keyname='ledger',
                start_ts=start_ts,
                end_ts=end_ts,
                extra_dict={},
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query kraken ledger between {start_ts} and '
                f'{end_ts}. {e!s}',
            )
            return [], start_ts

        new_events, _ = self.process_kraken_raw_events(
            events=response,
            events_source=f'{start_ts} to {end_ts}',
            save_skipped_events=True,
        )

        trade_events: list[HistoryEvent] = []
        adjustment_events: list[HistoryEvent] = []
        final_events: list[HistoryBaseEntry] = []
        for event in new_events:
            if event.event_type in {
                HistoryEventType.TRADE,
                HistoryEventType.RECEIVE,
                HistoryEventType.SPEND,
            }:
                trade_events.append(event)  # type: ignore[arg-type]  # will not be AssetMovement due to event_type check
            elif event.event_type == HistoryEventType.ADJUSTMENT:
                adjustment_events.append(event)  # type: ignore[arg-type]  # will not be AssetMovement due to event_type check
            else:
                final_events.append(event)

        swap_events, max_ts = self.process_kraken_trades(
            trade_events=trade_events,
            adjustments=adjustment_events,
        )
        final_events.extend(swap_events)
        return final_events, Timestamp(max_ts) if with_errors else end_ts

    def history_event_from_kraken(
            self,
            events: list[dict[str, Any]],
            save_skipped_events: bool,
    ) -> tuple[list[HistoryEvent | AssetMovement], bool, bool]:
        """
        This function gets raw data from kraken and creates a list of related history events
        to be used in the app. All events passed to this function have same refid.

        It returns a list of events, a boolean indicating events are skipped
        and a boolean in the case that an unknown type is found.

        If `save_skipped_events` is True then any events that are skipped are saved
        in the DB for processing later.

        Information on how to interpret Kraken ledger type field: https://support.kraken.com/hc/en-us/articles/360001169383-How-to-interpret-Ledger-history-fields
        """
        group_events: list[tuple[int, HistoryEvent | AssetMovement]] = []
        skipped = False
        # for receive/spend events they could be airdrops but they could also be instant swaps.
        # the only way to know if it was a trade is by finding a pair of receive/spend events.
        # This is why we collect them instead of directly pushing to group_events
        receive_spend_events: dict[str, list[tuple[int, HistoryEvent]]] = defaultdict(list)
        found_unknown_event = False
        current_fee_index = len(events)

        for idx, raw_event in enumerate(events):
            try:
                if skipped:  # bad: Using exception for control flow. This function needs refactor
                    raise DeserializationError('Hit a skipped event')

                identifier = raw_event['refid']
                timestamp = TimestampMS((deserialize_fval(
                    value=raw_event['time'], name='time', location='kraken ledger processing',
                ) * 1000).to_int(exact=False))

                event_type, event_subtype = kraken_ledger_entry_type_to_ours(raw_event['type'])
                asset = asset_from_kraken(raw_event['asset'])
                notes = None
                raw_amount = deserialize_fval(
                    raw_event['amount'],
                    name='event amount',
                    location='kraken ledger processing',
                )

                # If we don't know how to handle an event atm or we find an unsupported
                # event type the logic will be to store it as unknown and if in the future
                # we need some information from it we can take actions to process them
                if event_type == HistoryEventType.TRANSFER:
                    if raw_event['subtype'] == '':  # Internal kraken events
                        # Lefteris has seen it in: Crediting airdrops/fork coins
                        # such as ETC, BCH, BSV. OR the XXLM airdrop. Also for forced
                        # removal of a coin due to delisting(negative amount), which is followed
                        # by another similar transfer with positive amount. Also OTC
                        # or other private deals seem to have this type
                        event_type = HistoryEventType.ADJUSTMENT
                        event_subtype = HistoryEventSubType.SPEND if raw_amount < ZERO else HistoryEventSubType.RECEIVE  # noqa: E501
                    elif raw_event['subtype'] == 'spottostaking':
                        event_type = HistoryEventType.STAKING
                        event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    elif raw_event['subtype'] == 'stakingfromspot':
                        continue  # no need to have an event here. Covered by deposit_asset
                    elif raw_event['subtype'] == 'stakingtospot':
                        event_type = HistoryEventType.STAKING
                        event_subtype = HistoryEventSubType.REMOVE_ASSET
                    elif raw_event['subtype'] == 'spotfromstaking':
                        continue  # no need to have an event here - covered by remove_asset
                    elif raw_event['subtype'] == 'spotfromfutures':
                        # at least for lefteris the credit of ETHW is this type
                        event_type = HistoryEventType.ADJUSTMENT
                        event_subtype = HistoryEventSubType.RECEIVE

                elif event_type in (HistoryEventType.ADJUSTMENT, HistoryEventType.TRADE):
                    event_subtype = HistoryEventSubType.SPEND if raw_amount < ZERO else HistoryEventSubType.RECEIVE  # noqa: E501
                elif event_type == HistoryEventType.STAKING:
                    # in the case of ETH.S after the activation of withdrawals rewards no longer
                    # compound unlike what happens with other assets and a virtual event with
                    # negative amount is created
                    if asset == A_ETH2 and raw_amount < ZERO:
                        event_type = HistoryEventType.INFORMATIONAL
                        notes = 'Automatic virtual conversion of staked ETH rewards to ETH'
                    else:
                        event_subtype = HistoryEventSubType.REWARD
                elif event_type == HistoryEventType.INFORMATIONAL:
                    found_unknown_event = True
                    notes = raw_event['type']
                    log.warning(
                        f'Encountered kraken historic event type we do not process. {raw_event}',
                    )

                fee_amount = deserialize_asset_amount(raw_event['fee'])
                # check for failed events (events that cancel each other out -- like failed
                if (  # withdrawals). Compare if amounts cancel themselves out (also fee if exists)
                        len(events) == 2 and idx == 1 and
                        events[0]['type'] == events[1]['type'] and
                        events[0]['subtype'] == events[1]['subtype'] and
                        abs(raw_amount) == group_events[0][1].amount and (
                            len(group_events) != 2 or
                            abs(fee_amount) == group_events[1][1].amount)
                ):
                    log.info(f'Skipping failed kraken events that cancel each other out: {events}')
                    return [], skipped, False

                # Make sure to not generate an event for KFEES that is not of type FEE
                if asset != A_KFEE:
                    # Process asset movements - there are no KFEE deposit/withdrawal events
                    if event_type in {HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL}:
                        group_events.extend(
                            (idx, event) for event in create_asset_movement_with_fee(
                                timestamp=timestamp,
                                location=self.location,
                                location_label=self.name,
                                event_type=event_type,  # type: ignore  # will be deposit or withdrawal
                                asset=asset,
                                amount=abs(raw_amount),
                                fee_asset=asset,
                                fee=abs(fee_amount),
                                unique_id=identifier,
                            )
                        )
                        continue

                    history_event = HistoryEvent(
                        event_identifier=identifier,
                        sequence_index=idx,
                        timestamp=timestamp,
                        location=Location.KRAKEN,
                        location_label=self.name,
                        asset=asset,
                        amount=abs(raw_amount),  # amount sign was used above to determine types now enforce positive  # noqa: E501
                        notes=notes,
                        event_type=event_type,
                        event_subtype=event_subtype,
                    )
                    if history_event.event_type in (HistoryEventType.RECEIVE, HistoryEventType.SPEND):  # noqa: E501
                        receive_spend_events[history_event.event_identifier].append((idx, history_event))  # noqa: E501
                    else:
                        group_events.append((idx, history_event))
                if event_type != HistoryEventType.INFORMATIONAL and fee_amount != ZERO:  # avoid processing ignored events with fees that were converted to informational  # noqa: E501
                    group_events.append((idx, HistoryEvent(
                        event_identifier=identifier,
                        sequence_index=current_fee_index,
                        timestamp=timestamp,
                        location=Location.KRAKEN,
                        location_label=self.name,
                        asset=asset,
                        amount=abs(fee_amount),
                        notes=notes,
                        event_type=event_type if event_type != HistoryEventType.RECEIVE else HistoryEventType.SPEND,  # in instant swaps @tewshi found that fees can also be in the receive part  # noqa: E501
                        event_subtype=HistoryEventSubType.FEE,
                    )))
                    # Increase the fee index to not have duplicates in the case of having a normal
                    # fee and KFEE
                    current_fee_index += 1
            except (DeserializationError, KeyError, UnknownAsset) as e:
                skipped = True
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Keyrror {msg}'
                self.msg_aggregator.add_error(
                    f'Failed to read ledger event from kraken {raw_event} due to {msg}',
                )
                if save_skipped_events:
                    with self.db.user_write() as write_cursor:
                        self.db.add_skipped_external_event(
                            write_cursor=write_cursor,
                            location=Location.KRAKEN,
                            data=raw_event,
                            extra_data={'location_label': self.name},
                        )
                continue

        for event_set in receive_spend_events.values():
            if len(event_set) == 2:
                for _, history_event in event_set:
                    history_event.event_subtype = HistoryEventSubType.RECEIVE if history_event.event_type == HistoryEventType.RECEIVE else HistoryEventSubType.SPEND  # noqa: E501
                    history_event.event_type = HistoryEventType.TRADE

            # make sure to add all the events to group_events
            group_events.extend(event_set)

        returned_events = []
        for raw_event_idx, event in group_events:
            if skipped:  # add it also to skipped events if another event with same refid had to be skipped  # noqa: E501
                with self.db.user_write() as write_cursor:
                    self.db.add_skipped_external_event(
                        write_cursor=write_cursor,
                        location=Location.KRAKEN,
                        data=events[raw_event_idx],
                        extra_data={'location_label': self.name},
                    )
                continue
            if event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND:  # noqa: E501
                event.sequence_index = 0
            elif event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE:  # noqa: E501
                event.sequence_index = 1

            returned_events.append(event)

        return returned_events, skipped, found_unknown_event
