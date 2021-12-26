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
from itertools import permutations
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlencode

import gevent
import requests
from requests import Response

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import (
    AssetBalance,
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import KRAKEN_TO_WORLD, WORLD_TO_KRAKEN, asset_from_kraken
from rotkehlchen.constants import KRAKEN_API_VERSION, KRAKEN_BASE_URL
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2, A_KFEE
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors import (
    DeserializationError,
    InputError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category,
    deserialize_timestamp_from_kraken,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KRAKEN_DELISTED = ('XDAO', 'XXVN', 'ZKRW', 'XNMC', 'BSV', 'XICN')
KRAKEN_PUBLIC_METHODS = ('AssetPairs', 'Assets')
KRAKEN_QUERY_TRIES = 8
KRAKEN_BACKOFF_DIVIDEND = 15
MAX_CALL_COUNTER_INCREASE = 2  # Trades and Ledger produce the max increase


def kraken_to_world_pair(pair: str) -> Tuple[Asset, Asset]:
    """Turns a pair from kraken to our base/quote asset tuple

    Can throw:
        - UknownAsset if one of the assets of the pair are not known
        - DeserializationError if one of the assets is not a sting
        - UnprocessableTradePair if the pair can't be processed and
          split into its base/quote assets
"""
    # handle dark pool pairs
    if pair[-2:] == '.d':
        pair = pair[:-2]

    if len(pair) == 6 and pair[0:3] in ('EUR', 'USD', 'AUD'):
        # This is for the FIAT to FIAT pairs that kraken introduced
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair == 'ETHDAI':
        return A_ETH, A_DAI
    elif pair == 'ETH2.SETH':
        return A_ETH2, A_ETH
    elif pair[0:2] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:2]
        quote_asset_str = pair[2:]
    elif pair[0:3] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair[0:3] in ('XBT', 'ETH', 'XDG', 'LTC', 'XRP'):
        # Some assets can have the 'X' prefix omitted for some pairs
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair[0:4] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:4]
        quote_asset_str = pair[4:]
    elif pair[0:5] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:5]
        quote_asset_str = pair[5:]
    elif pair[0:6] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:6]
        quote_asset_str = pair[6:]
    else:
        raise UnprocessableTradePair(pair)

    base_asset = asset_from_kraken(base_asset_str)
    quote_asset = asset_from_kraken(quote_asset_str)
    return base_asset, quote_asset


def history_event_from_kraken(
    events: List[Dict[str, Any]],
    name: str,
    msg_aggregator: MessagesAggregator,
) -> Tuple[List[HistoryBaseEntry], bool]:
    """
    This function gets raw data from kraken and creates a list of related history events
    to be used in the app. It returns a list of events and a boolean in the case that an unknown
    type is found.
    """
    group_events = []
    found_unknown_event = False
    for idx, raw_event in enumerate(events):
        try:
            timestamp = deserialize_timestamp_from_kraken(raw_event['time'])
            identifier = raw_event['refid']
            event_type = HistoryEventType.from_string(raw_event['type'])
            asset = asset_from_kraken(raw_event['asset'])
            event_subtype = None
            amount = abs(deserialize_asset_amount(raw_event['amount']))
            # If we don't know how to handle an event atm or we find an unsupported
            # event type the logic will be to store it as unknown and if in the future
            # we need some information from it we can take actions to process them
            if event_type == HistoryEventType.TRANSFER:
                if raw_event['subtype'] == 'spottostaking':
                    event_type = HistoryEventType.STAKING
                    event_subtype = HistoryEventSubType.STAKING_DEPOSIT_ASSET
                elif raw_event['subtype'] == 'stakingfromspot':
                    event_type = HistoryEventType.STAKING
                    event_subtype = HistoryEventSubType.STAKING_RECEIVE_ASSET
                elif raw_event['subtype'] == 'stakingtospot':
                    event_type = HistoryEventType.UNSTAKING
                    event_subtype = HistoryEventSubType.STAKING_REMOVE_ASSET
                elif raw_event['subtype'] == 'spotfromstaking':
                    event_type = HistoryEventType.UNSTAKING
                    event_subtype = HistoryEventSubType.STAKING_RECEIVE_ASSET
            elif event_type == HistoryEventType.UNKNOWN:
                found_unknown_event = True
                msg_aggregator.add_warning(
                    f'Encountered unknown kraken historic event type {raw_event["type"]}. Event '
                    f'will be stored but not processed.',
                )
            fee = deserialize_asset_amount(raw_event['fee'])

            group_events.append(HistoryBaseEntry(
                event_identifier=identifier,
                sequence_index=idx,
                timestamp=timestamp,
                location=Location.KRAKEN,
                location_label=name,
                amount=AssetBalance(
                    asset=asset,
                    balance=Balance(
                        amount=amount,
                        usd_value=ZERO,
                    ),
                ),
                notes=None,
                event_type=event_type,
                event_subtype=event_subtype,
            ))
            if fee != ZERO:
                group_events.append(HistoryBaseEntry(
                    event_identifier=identifier,
                    sequence_index=len(events),
                    timestamp=timestamp,
                    location=Location.KRAKEN,
                    location_label=name,
                    amount=AssetBalance(
                        asset=asset,
                        balance=Balance(
                            amount=fee,
                            usd_value=ZERO,
                        ),
                    ),
                    notes=None,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.FEE,
                ))
        except (DeserializationError, KeyError, UnknownAsset) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Keyrror {msg}'
            msg_aggregator.add_error(
                f'Failed to read ledger event from kraken {raw_event} due to {msg}',
            )
            return [], False
    return group_events, found_unknown_event


def _check_and_get_response(response: Response, method: str) -> Union[str, Dict]:
    """Checks the kraken response and if it's succesfull returns the result.

    If there is recoverable error a string is returned explaining the error
    May raise:
    - RemoteError if there is an unrecoverable/unexpected remote error
    """
    if response.status_code in (520, 525, 504):
        log.debug(f'Kraken returned status code {response.status_code}')
        return 'Usual kraken 5xx shenanigans'
    if response.status_code != 200:
        raise RemoteError(
            'Kraken API request {} for {} failed with HTTP status '
            'code: {}'.format(
                response.url,
                method,
                response.status_code,
            ))

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


class KrakenAccountType(SerializableEnumMixin):
    STARTER = 0
    INTERMEDIATE = 1
    PRO = 2


DEFAULT_KRAKEN_ACCOUNT_TYPE = KrakenAccountType.STARTER


class Kraken(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            kraken_account_type: Optional[KrakenAccountType] = None,
    ):
        super().__init__(
            name=name,
            location=Location.KRAKEN,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({'API-Key': self.api_key})
        self.set_account_type(kraken_account_type)
        self.call_counter = 0
        self.last_query_ts = 0
        self.pairs: Set[str] = set()

    def set_account_type(self, account_type: Optional[KrakenAccountType]) -> None:
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

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'API-Key': self.api_key})

        return changed

    def edit_exchange(
            self,
            name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            **kwargs: Any,
    ) -> Tuple[bool, str]:
        success, msg = super().edit_exchange(
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            **kwargs,
        )
        if success is False:
            return success, msg

        account_type = kwargs.get('kraken_account_type')
        if account_type is None:
            return success, msg

        # here we can finally update the account type
        self.set_account_type(account_type)
        return True, ''

    def validate_api_key(self) -> Tuple[bool, str]:
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
            method_str: str,
            req: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
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
            log.error(f'Kraken API key validation error: {str(e)}')
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
        if method in ('Ledgers', 'TradesHistory'):
            self.call_counter += 2
        else:
            self.call_counter += 1

    def _query_public(self, method: str, req: Optional[dict] = None) -> Union[Dict, str]:
        """API queries that do not require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})
        """
        if req is None:
            req = {}
        urlpath = f'{KRAKEN_BASE_URL}/{KRAKEN_API_VERSION}/public/{method}'
        try:
            response = self.session.post(urlpath, data=req, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {str(e)}') from e

        self._manage_call_counter(method)
        return _check_and_get_response(response, method)

    def api_query(self, method: str, req: Optional[dict] = None) -> dict:
        tries = KRAKEN_QUERY_TRIES
        query_method = (
            self._query_public if method in KRAKEN_PUBLIC_METHODS else self._query_private
        )
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
            result = query_method(method, req)
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

    def _query_private(self, method: str, req: Optional[dict] = None) -> Union[Dict, str]:
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
            'API-Sign': base64.b64encode(signature.digest()),  # type: ignore
        })
        try:
            response = self.session.post(
                KRAKEN_BASE_URL + urlpath,
                data=post_data.encode(),
                timeout=DEFAULT_TIMEOUT_TUPLE,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {str(e)}') from e
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
                    'to {}'.format(e)
                )
                log.error(msg)
                return None, msg

        assets_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for kraken_name, amount_ in kraken_balances.items():
            try:
                amount = deserialize_asset_amount(amount_)
                if amount == ZERO:
                    continue

                our_asset = asset_from_kraken(kraken_name)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown kraken asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except DeserializationError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    'Error processing kraken balance for {kraken_name}. Check logs '
                    'for details. Ignoring it.',
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
                # There is no price value for KFEE. TODO: Shouldn't we then just skip the balance?
                try:
                    usd_price = Inquirer().find_usd_price(our_asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing kraken balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
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
            endpoint: str,
            keyname: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            extra_dict: Optional[dict] = None,
    ) -> Tuple[List, bool]:
        """ Abstracting away the functionality of querying a kraken endpoint where
        you need to check the 'count' of the returned results and provide sufficient
        calls with enough offset to gather all the data of your query.
        """
        result: List = []

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
                    f'with {str(e)}. Returning only results we have.',
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
                    'Missing {} results when querying kraken endpoint {}'.format(
                        count - offset, endpoint),
                )
                with_errors = True
                break

            result.extend(response[keyname].values())

        return result, with_errors

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        """
        Query kraken events from database and create trades from them. May raise:
        - RemoteError if the kraken pairs couldn't be queried
        """
        queried_range = self.query_kraken_ledgers(start_ts=start_ts, end_ts=end_ts)
        filter_query = HistoryEventFilterQuery.make(
            from_ts=start_ts,
            to_ts=end_ts,
            event_type=[
                HistoryEventType.TRADE,
                HistoryEventType.RECEIVE,
                HistoryEventType.SPEND,
            ],
            location=Location.KRAKEN,
            location_label=self.name,
        )
        trades_raw = self.db.get_history_events(filter_query)
        trades = self.process_kraken_trades(trades_raw)
        return trades, queried_range

    def _query_endpoint_for_period(
            self,
            endpoint: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            offset: Optional[int] = None,
            extra_dict: Optional[dict] = None,
    ) -> dict:
        request: Dict[str, Union[Timestamp, int]] = {}
        request['start'] = start_ts
        request['end'] = end_ts
        if offset is not None:
            request['ofs'] = offset
        if extra_dict is not None:
            request.update(extra_dict)
        result = self.api_query(endpoint, request)
        return result

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        self.query_kraken_ledgers(start_ts=start_ts, end_ts=end_ts)
        filter_query = HistoryEventFilterQuery.make(
            from_ts=start_ts,
            to_ts=end_ts,
            event_type=[
                HistoryEventType.DEPOSIT,
                HistoryEventType.WITHDRAWAL,
            ],
            location=Location.KRAKEN,
            location_label=self.name,
        )
        events = self.db.get_history_events(filter_query)
        log.debug('Kraken deposit/withdrawals query result', num_results=len(events))
        movements = []
        get_attr = operator.attrgetter('event_identifier')
        # Create a list of lists where each sublist has the events for the same event identifier
        grouped_events = [list(g) for k, g in itertools.groupby(sorted(events, key=get_attr), get_attr)]  # noqa: E501
        for movement_events in grouped_events:
            if len(movement_events) == 2:
                if movement_events[0].event_subtype == HistoryEventSubType.FEE:
                    fee = Fee(movement_events[0].amount.balance.amount)
                    movement = movement_events[1]
                elif movement_events[1].event_subtype == HistoryEventSubType.FEE:
                    fee = Fee(movement_events[1].amount.balance.amount)
                    movement = movement_events[0]
                else:
                    self.msg_aggregator.add_error(
                        f'Failed to process deposit/withdrawal. {grouped_events}. Ignoring ...',
                    )
                    continue
            else:
                movement = movement_events[0]
                fee = Fee(ZERO)
            try:
                asset = movement.amount.asset
                movement_type = movement.event_type
                movements.append(AssetMovement(
                    location=Location.KRAKEN,
                    category=deserialize_asset_movement_category(movement_type),
                    timestamp=movement.timestamp,
                    address=None,  # no data from kraken ledger endpoint
                    transaction_id=None,  # no data from kraken ledger endpoint
                    asset=asset,
                    amount=movement.amount.balance.amount,
                    fee_asset=asset,
                    fee=fee,
                    link=movement.event_identifier,
                ))
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown kraken asset {e.asset_name}. '
                    f'Ignoring its deposit/withdrawals query.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kraken deposit/withdrawals. '
                    'Check logs for details. Ignoring it.',
                )
                log.error(
                    'Error processing a kraken deposit/withdrawal.',
                    raw_asset_movement=movement_events,
                    error=msg,
                )
                continue

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for kraken

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for kraken

    def query_pairs_if_needed(self) -> None:
        if len(self.pairs) == 0:
            self.pairs = set(self.api_query('AssetPairs').keys())

    def kraken_asset_to_pair(self, asset1: Asset, asset2: Asset) -> Optional[str]:
        """Given a pair of assets find the kraken pair that has these two assets as
        base and quote.
        Precondition: It requires that the self.pairs list is populated to properly work.
        """
        asset1_symbol, asset2_symbol = asset1.symbol, asset2.symbol
        asset1_kraken_tr = WORLD_TO_KRAKEN.get(asset1_symbol, asset1_symbol)
        asset2_kraken_tr = WORLD_TO_KRAKEN.get(asset2_symbol, asset2_symbol)

        for a, b in permutations(
            [
                ('a', asset1_symbol),
                ('b', asset2_symbol),
                ('a', asset1_kraken_tr),
                ('b', asset2_kraken_tr),
            ],
            2,
        ):
            if a[0] == b[0]:
                continue
            pair_candidate = a[1] + b[1]
            if pair_candidate in self.pairs:
                return pair_candidate
        return None

    def process_kraken_trades(
        self,
        raw_data: List[HistoryBaseEntry],
    ) -> List[Trade]:
        """
        Given a list of history events we process them to create Trade objects. The valid
        History events type are
        - Trade
        - Receive
        - Spend

        A pair of receive and spend events can be a trade and kraken uses this kind of event
        for instant trades and trades made from the phone app. What we do in order to verify
        that it is a trade is to check if we can find a pair with the same event id.

        May raise:
        - RemoteError if the pairs couldn't be correctly queried
        """
        self.query_pairs_if_needed()
        trades = []
        get_attr = operator.attrgetter('event_identifier')
        # Create a list of lists where each sublist has the events for the same event identifier
        grouped_events = [list(g) for k, g in itertools.groupby(sorted(raw_data, key=get_attr), get_attr)]  # noqa: E501
        for trade_parts in grouped_events:
            event_id = trade_parts[0].event_identifier
            is_spend_receive = False
            trade_assets = []

            for trade_part in trade_parts:
                if trade_part.event_type == HistoryEventType.RECEIVE:
                    is_spend_receive = True
                if (
                    trade_part.amount.balance.amount != ZERO and
                    trade_part.event_subtype != HistoryEventSubType.FEE
                ):
                    trade_assets.append(trade_part.amount.asset)

            if is_spend_receive and len(trade_parts) < 2:
                continue

            if len(trade_assets) != 2:
                self.msg_aggregator.add_error(
                    f'Found kraken trade event {event_id} with more '
                    f'than two assets involved. Skipping...',
                )
                continue

            pair = self.kraken_asset_to_pair(trade_assets[0], trade_assets[1])
            if pair is None:
                self.msg_aggregator.add_error(
                    f'Couldnt find Kraken pair for assets {trade_assets} and '
                    f'trade id {event_id}. Skipping trade',
                )
                continue

            base_asset, quote_asset = kraken_to_world_pair(pair)
            timestamp = trade_parts[0].timestamp
            # Now in the parts in which we break the events we try to find the
            # base/quote parts and the fee. It might be possible that kfee was used
            # so we also search for it
            base_trade, quote_trade, fee_part, kfee_part = None, None, None, None
            for trade_part in trade_parts:
                part_asset = trade_part.amount.asset
                if trade_part.event_subtype == HistoryEventSubType.FEE:
                    fee_part = trade_part
                elif trade_part.amount.asset == A_KFEE:
                    kfee_part = trade_part
                elif part_asset == base_asset:
                    base_trade = trade_part
                elif part_asset == quote_asset:
                    quote_trade = trade_part

            if base_trade is None or quote_trade is None:
                log.error(f'Failed to process {event_id} with parts {trade_parts}')
                self.msg_aggregator.add_error(
                    f'Failed to read trades for event {event_id}. '
                    f'More details are available at the logs',
                )
                continue

            base_amount = base_trade.amount.balance.amount
            quote_amount = quote_trade.amount.balance.amount

            if quote_amount < 0:
                trade_type = TradeType.SELL
                amount = base_amount
                received_asset = quote_trade.amount.asset
            else:
                trade_type = TradeType.BUY
                amount = quote_amount
                received_asset = base_trade.amount.asset

            if base_amount != ZERO:
                rate = Price(quote_amount / base_amount)
            else:
                self.msg_aggregator.add_error(
                    f'Rate for kraken trade couldnt be calculated. Base amount is ZERO '
                    f'for event {event_id}',
                )
                continue

            exchange_uuid = (
                str(event_id) +
                str(timestamp)
            )
            # If kfee was found we use it as the fee for the trade
            if kfee_part is not None:
                fee = Fee(kfee_part.amount.balance.amount)
                fee_asset = A_KFEE
            elif (None, None) == (fee_part, kfee_part):
                fee = Fee(ZERO)
                fee_asset = received_asset
            elif fee_part is not None:
                fee = Fee(fee_part.amount.balance.amount)
                fee_asset = fee_part.amount.asset

            trade = Trade(
                timestamp=timestamp,
                location=Location.KRAKEN,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=AssetAmount(amount),
                rate=rate,
                fee=fee,
                fee_currency=fee_asset,
                link=exchange_uuid,
            )
            trades.append(trade)
        return trades

    @protect_with_lock()
    def query_kraken_ledgers(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> Tuple[Timestamp, Timestamp]:
        """
        Query Kraken's ledger to retrieve events and transform them to our internal representation
        of history events.
        """
        response, with_errors = self.query_until_finished(
            endpoint='Ledgers',
            keyname='ledger',
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict={},
        )
        # Group related events
        raw_events_groupped = defaultdict(list)
        for raw_event in response:
            raw_events_groupped[raw_event['refid']].append(raw_event)

        new_events = []
        max_ts = 0
        for events in raw_events_groupped.values():
            try:
                events = sorted(
                    events,
                    key=lambda x: deserialize_timestamp_from_kraken(x['time']),
                )
                max_ts = max(max_ts, deserialize_timestamp_from_kraken(events[-1]['time']))
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Failed to read timestamp in kraken event group '
                    f'due to {str(e)}. For more information read the logs. Skipping event',
                )
                log.error(f'Failed to read timestamp for {events}')
                continue
            group_events, found_unknown_event = history_event_from_kraken(
                events=events,
                name=self.name,
                msg_aggregator=self.msg_aggregator,
            )
            if found_unknown_event:
                for event in group_events:
                    event.event_type = HistoryEventType.UNKNOWN
            new_events.extend(group_events)

        if len(new_events) != 0:
            try:
                self.db.add_history_events(new_events)
            except InputError as e:
                self.msg_aggregator.add_error(
                    f'Failed to save kraken events from {start_ts} to {end_ts} '
                    f'in database. {str(e)}',
                )

        queried_range = (start_ts, Timestamp(max_ts)) if with_errors else (start_ts, end_ts)
        return queried_range
