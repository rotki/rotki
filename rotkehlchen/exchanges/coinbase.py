import hashlib
import hmac
import logging
import re
import secrets
import time
from collections import defaultdict
from collections.abc import Sequence
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import jwt
import requests
from cryptography.hazmat.primitives import serialization

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_force_positive,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Price,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import combine_dicts, ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.types import Asset, TimestampMS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

CB_EVENTS_PREFIX = 'CBE_'
CB_VERSION = '2019-08-25'  # the latest api version we know rotki works fine for: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/versioning  # noqa: E501
LEGACY_RE: re.Pattern = re.compile(r'^[\w]+$')
NEW_RE: re.Pattern = re.compile(r'^organizations/[\w-]+/apiKeys/[\w-]+$')
PRIVATE_KEY_RE: re.Pattern = re.compile(
    r'^-----BEGIN EC PRIVATE KEY-----\n'
    r'[\w+/=\n]+'
    r'-----END EC PRIVATE KEY-----\n?$',
    re.MULTILINE,
)


class CoinbasePermissionError(Exception):
    pass


class Coinbase(ExchangeInterface):

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
            location=Location.COINBASE,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.apiversion = CB_VERSION
        self.base_uri = 'https://api.coinbase.com'
        self.legacy = bool(LEGACY_RE.match(api_key))
        self.advanced = not self.legacy
        if self.advanced:
            self.session.headers.update({
                'User-Agent': 'rotki',
                'Content-Type': 'application/json',
            })

    def first_connection(self) -> None:
        self.first_connection_made = True

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Coinbase API key is good for usage in rotki
        Makes sure that the following permissions are given to the key:
        - wallet:accounts:read
        - wallet:transactions:read
        - wallet:orders:read
        - wallet:trades:read
        If any of these is not given the key is not valid
        """
        try:
            result = self._api_query('user')
        except (RemoteError, CoinbasePermissionError) as e:
            return False, str(e)

        if 'errors' in result:
            return False, result['errors'][0]['message']

        return True, ''

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.legacy = bool(LEGACY_RE.match(credentials.api_key))
            self.advanced = not self.legacy

        return changed

    def _generate_signature(self, req: requests.PreparedRequest) -> tuple[str, str]:
        """Legacy signature"""
        timestamp = str(int(time.time()))
        message = timestamp + req.method + req.path_url

        if req.body:
            message += req.body.decode()

        signature = hmac.new(self.secret, message.encode(), hashlib.sha256).hexdigest()

        return timestamp, signature

    def _generate_advanced_signature(self, req: requests.PreparedRequest) -> tuple[str, str]:
        """CB Advanced Trade signature"""
        timestamp = str(int(time.time()))
        message = timestamp + req.method + req.path_url.split('?')[0]

        signature = hmac.new(self.secret, message.encode(), hashlib.sha256).hexdigest()

        return timestamp, signature

    def _generate_jwt(self, req: requests.PreparedRequest) -> str:
        """CB Cloud signature (legacy API replacement)"""
        timestamp = int(time.time())
        request = req.method + ' ' + self.base_uri.split('/', 3)[2] + req.path_url
        jwt_payload = {
            'sub': self.api_key,
            'iss': 'coinbase-cloud',
            'nbf': timestamp,
            'exp': timestamp + 60,
            'aud': ['retail_rest_api_proxy'],
            'uri': request,
        }

        # Parse the private key
        key = serialization.load_pem_private_key(self.secret, password=None)

        # Generate JWT token
        return jwt.encode(
            jwt_payload,
            key,  # type: ignore[arg-type]
            algorithm='ES256',
            headers={'kid': self.api_key, 'typ': 'JWT', 'alg': 'ES256', 'nonce': secrets.token_hex(16)},
        )

    def _api_query(
            self,
            endpoint: str,
            request_method: Literal['GET', 'POST'] = 'GET',
            options: dict[str, Any] | None = None,
            authenticated: bool = True,
            advanced_api: bool = False,
    ) -> dict[str, Any]:
        """Performs a coinbase API Query for endpoint
        - Coinbase legacy authentication: using the HMAC-SHA256 signing
        - Coinbase cloud authentication: using the ES256 JWT signing
        - Coinbase advanced api authentication: using the HMAC-SHA256 signing

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        Raises CoinbasePermissionError if the API Key does not have sufficient
        permissions for the endpoint
        """
        request_url = self.base_uri + '/v2/' + endpoint
        retries_left = CachedSettings().get_query_retry_limit()
        timeout_tuple = CachedSettings().get_timeout_tuple()

        if options is not None and request_method == 'GET':
            request_url += '?' + urlencode(options)
        if authenticated and advanced_api:
            request_url = self.base_uri + '/api/v3/brokerage/' + endpoint
            self.apiversion = '2024-08-27'

        log.debug('Coinbase API Query', request_url=request_url)

        def _do_query():
            nonlocal options
            if authenticated:
                if self.legacy:
                    req = requests.Request(
                        request_method,
                        request_url,
                        json=options if request_method == 'POST' else None,
                    )
                    prepped = req.prepare()
                    timestamp, signature = self._generate_signature(prepped)
                    self.session.headers.update({
                        'CB-ACCESS-KEY': self.api_key,
                        'CB-ACCESS-SIGN': signature,
                        'CB-ACCESS-TIMESTAMP': timestamp,
                        'CB-VERSION': self.apiversion,
                    })
                elif advanced_api:
                    req = requests.Request(
                        request_method,
                        request_url,
                        json=options if request_method == 'POST' else None,
                    )
                    prepped = req.prepare()
                    timestamp, signature = self._generate_advanced_signature(prepped)
                    self.session.headers.update({
                        'CB-ACCESS-KEY': self.api_key,
                        'CB-ACCESS-SIGN': signature,
                        'CB-ACCESS-TIMESTAMP': timestamp,
                    })
                else:
                    req = requests.Request(
                        request_method,
                        request_url,
                        json=options if request_method == 'POST' else None,
                    )
                    prepped = req.prepare()
                    jwt_token = self._generate_jwt(prepped)
                    self.session.headers.update({
                        'Authorization': f'Bearer {jwt_token}',
                    })

            if request_method == 'GET':
                response = self.session.get(request_url, timeout=timeout_tuple)
            else:
                response = self.session.post(request_url, json=options, timeout=timeout_tuple)

            if response.status_code == 429:
                raise RemoteError('Coinbase: Rate limit exceeded')

            if response.status_code == 403:
                raise CoinbasePermissionError(
                    f'API Key does not have permission for {endpoint}',
                )

            if response.status_code == 404:
                raise RemoteError(f'Coinbase: Endpoint {endpoint} not found')

            if response.status_code == 400:
                try:
                    result = jsonloads_dict(response.text)
                except JSONDecodeError as e:
                    raise RemoteError(
                        f'Coinbase: Error in API response {response.status_code}. '
                        f'Could not parse JSON: {response.text}',
                    ) from e

                raise RemoteError(
                    f'Coinbase: {result.get("message", "Bad Request")}',
                )

            if response.status_code != 200:
                raise RemoteError(
                    f'Coinbase: Error in API response {response.status_code}. '
                    f'Response: {response.text}',
                )

            try:
                result = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Coinbase: Error in API response. Could not parse JSON: {response.text}',
                ) from e

            return result

        while retries_left > 0:
            try:
                return _do_query()
            except RemoteError as e:
                error_message = str(e)
                if 'Rate limit exceeded' in error_message:
                    backoff_seconds = 20 / retries_left
                    retries_left -= 1
                    log.debug(
                        f'Coinbase: Got rate limited. Backing off for {backoff_seconds} seconds. '
                        f'{retries_left} retries left.',
                    )
                    time.sleep(backoff_seconds)
                else:
                    raise

        raise RemoteError('Coinbase: Ran out of retries for API query')

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            if self.legacy:
                accounts = self._query_accounts()
            else:
                accounts = self._query_accounts_cloud()
        except (RemoteError, CoinbasePermissionError) as e:
            msg = f'Coinbase: Error querying accounts: {e!s}'
            return None, msg

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for account in accounts:
            try:
                balance = deserialize_fval(account['balance']['amount'])
                # ignore empty balances
                if balance == ZERO:
                    continue

                asset = asset_from_coinbase(account['balance']['currency'])
                if asset is None:
                    continue

                usd_price = Inquirer.find_usd_price(asset=asset)
                assets_balance[asset] += Balance(
                    amount=balance,
                    usd_value=balance * usd_price,
                )
            except (RemoteError, KeyError, DeserializationError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error processing coinbase balance for '
                    f'{account["balance"]["currency"]}. {msg}',
                )
                log.error(
                    'Error processing coinbase balance',
                    account_currency=account['balance']['currency'],
                    error=msg,
                )
                continue
            except (UnknownAsset, UnsupportedAsset) as e:
                if isinstance(e, UnknownAsset):
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='balance query',
                    )
                continue

        return dict(assets_balance), ''

    def _query_accounts(self) -> list[dict[str, Any]]:
        """Query coinbase accounts using the legacy API"""
        path = 'accounts'
        accounts = []
        next_uri = None

        while True:
            if next_uri is None:
                # Need to ask for more balances per page to avoid rate limiting
                # the largest I could make it was 200
                options = {'limit': 200}
                response = self._api_query(path, options=options)
            else:
                response = self._api_query(next_uri.replace('/v2/', ''))

            if 'data' not in response:
                raise RemoteError(
                    f'Coinbase: Response does not contain data. Response: {response}',
                )

            accounts.extend(response['data'])

            pagination = response.get('pagination', {})
            next_uri = pagination.get('next_uri')

            if next_uri is None:
                break  # no more pages

        return accounts

    def _query_accounts_cloud(self) -> list[dict[str, Any]]:
        """Query coinbase accounts using the cloud API (legacy API replacement)"""
        path = 'accounts?limit=250'
        accounts = []
        next_page_cursor = None

        while True:
            if next_page_cursor is not None:
                path = f'accounts?limit=250&cursor={next_page_cursor}'

            response = self._api_query(path)

            if 'accounts' not in response:
                raise RemoteError(
                    f'Coinbase: Response does not contain accounts. Response: {response}',
                )

            for account in response['accounts']:
                accounts.append({
                    'balance': {
                        'amount': account['available_balance']['value'],
                        'currency': account['available_balance']['currency'],
                    },
                    'currency': account['currency'],
                    'id': account['uuid'],
                    'name': account['name'],
                    'type': account['type'],
                })

            has_next = response.get('has_next', False)
            next_page_cursor = response.get('cursor')

            if not has_next or next_page_cursor is None:
                break  # no more pages

        return accounts

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Query coinbase transactions history and save events in the DB.

        Coinbase requirements for the query of transactions:
            - If account_id is not specified, transactions of all accounts are returned.
            - type is optional, but if specified, only transactions of that type are returned.
        """
        # Query all transactions starting from the last time we did that (or the start)
        result = []
        for event in self._query_transactions(start_ts=start_ts, end_ts=end_ts):
            try:
                result.extend(self._process_transaction_event(event))
            except (UnknownAsset, UnsupportedAsset, DeserializationError, KeyError) as e:
                # TODO: Handle errors better
                log.error(
                    f'Failed to process coinbase transaction: {e}',
                    event=event,
                )
                continue

        if self.advanced:
            try:
                result.extend(self._query_cb_advanced_trades(start_ts=start_ts, end_ts=end_ts))
            except (RemoteError, CoinbasePermissionError, DeserializationError, KeyError) as e:
                # Handle specific errors
                if isinstance(e, CoinbasePermissionError):
                    log.warning(
                        'Advanced Trade API permission denied. '
                        'Skipping Coinbase Advanced trades query.',
                    )
                else:
                    log.error(
                        f'Failed to query Coinbase Advanced trades: {e!s}. '
                        'Try to add the necessary scopes and permissions to the API key '
                        'or use the legacy Coinbase API.',
                    )

        return result, end_ts

    def _query_transactions(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[dict[str, Any]]:
        """Query all coinbase transactions for all accounts"""
        transactions = []
        accounts = self._query_accounts() if self.legacy else self._query_accounts_cloud()

        for account in accounts:
            next_uri = None
            last_id = None
            while True:
                # Query pagination
                if next_uri is not None:
                    response = self._api_query(next_uri.replace('/v2/', ''))
                else:
                    # Need to ask for more transactions per page to avoid rate limiting
                    # For the initial query we need to check whether any transactions
                    # exist already in the database
                    account_id = account['id']
                    db_events = self._get_db_events(
                        account_id=account_id,
                        start_ts=start_ts,
                        end_ts=end_ts,
                    )
                    options = {'limit': 100, 'order': 'asc'}
                    if len(db_events) != 0:
                        # We have queried this account before
                        # Get the last event and query from there
                        last_event = max(db_events, key=lambda x: x.timestamp)
                        options['starting_after'] = last_event.extra_data.get('transaction_id')
                        if options['starting_after'] is None:
                            log.error(
                                f'Failed to find transaction_id for last event of {account_id}',
                            )
                            # Query all transactions for this account
                    response = self._api_query(
                        f'accounts/{account_id}/transactions',
                        options=options,
                    )

                if 'data' not in response:
                    raise RemoteError(
                        f'Coinbase: Response does not contain data. Response: {response}',
                    )

                for transaction in response['data']:
                    timestamp = deserialize_timestamp_from_date(
                        date=transaction['created_at'],
                        formatstr='%Y-%m-%dT%H:%M:%SZ',
                        location='coinbase',
                    )
                    # Skip old transactions or the ones in the future (Bug in coinbase)
                    if timestamp < start_ts or timestamp > end_ts:
                        continue

                    # Ensure that we progress in time
                    if last_id is not None and transaction['id'] == last_id:
                        log.warning(
                            f'Coinbase: Same transaction id {last_id} encountered twice',
                        )
                        break

                    last_id = transaction['id']
                    transactions.append(transaction)

                pagination = response.get('pagination', {})
                next_uri = pagination.get('next_uri')

                if next_uri is None:
                    break  # no more pages

        return transactions

    def _get_db_events(
            self,
            account_id: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Get coinbase events from the database for the given account"""
        with self.db.conn.read_ctx() as cursor:
            db_entries = DBHistoryEvents(self.db).get_history_events(
                cursor=cursor,
                filter_query=DBHistoryEvents.prepare_filter_query(
                    location=Location.COINBASE,
                    from_ts=start_ts,
                    to_ts=end_ts,
                ),
                has_premium=True,  # not limiting here
            )

        events = []
        for entry in db_entries:
            if entry.extra_data is not None and entry.extra_data.get('account_id') == account_id:
                events.append(entry)

        return events

    def _process_transaction_event(
            self,
            transaction: dict[str, Any],
    ) -> list['HistoryBaseEntry']:
        """Process a single coinbase transaction and convert to rotki events"""
        # Implement transaction processing logic here
        # This is a placeholder - the actual implementation would convert
        # coinbase transactions to the appropriate event types
        return []

    def _query_cb_advanced_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Query Coinbase Advanced Trade API for trades"""
        # Placeholder for advanced trade querying
        return []

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for coinbase