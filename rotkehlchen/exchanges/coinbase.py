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

import gevent
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
        try:
            self.is_legacy_api_key = self.is_legacy_key(api_key)
        except AuthenticationError as e:
            self.is_legacy_api_key = True
            log.error(f'Error determining API key format: {e}. Defaulting to legacy key.')

        if self.is_legacy_api_key:  # set headers for legacy
            self.session.headers.update({'CB-ACCESS-KEY': self.api_key, 'CB-VERSION': CB_VERSION})

        self.apiversion = 'v2'
        self.base_uri = 'https://api.coinbase.com'
        self.host = 'api.coinbase.com'
        # Maps advanced trade order ids to the trade currency so unneeded events can be
        # skipped when both the debit and credit part of the trade is present.
        self.advanced_orders_to_currency: dict[str, str] = {}
        self.staking_events: set[tuple[TimestampMS, Asset, FVal]] = set()

    def is_legacy_key(self, api_key: str) -> bool:
        if LEGACY_RE.match(api_key):
            log.debug('Legacy Key format!')
            return True
        elif NEW_RE.match(api_key):
            log.debug('New Key format!')
            return False
        else:
            raise AuthenticationError(f'Invalid API key format: {api_key}')

    def first_connection(self) -> None:
        self.first_connection_made = True

    def build_jwt(self, uri: str) -> str:
        """Builds a JWT token for authentication with the Coinbase API.
        The JWT token is built using the provided URI and the stored API key name and private key.
        The token includes the following claims:
        - 'sub': The API key name.
        - 'iss': The issuer, which is set to "coinbase-cloud".
        - 'nbf': The "not before" timestamp, set to the current time.
        - 'exp': The expiration timestamp, set to 2 minutes from the current time.
        - 'uri': The provided URI.

        The token is signed using the ES256 algorithm and includes a unique 'nonce' in the headers.

        Args:
            uri (str): The URI for which the JWT token is being generated.

        Returns:
            str: The generated JWT token.

        Raises:
            RemoteError: If there is an error during the JWT token generation process.
        """
        try:
            private_key = serialization.load_pem_private_key(self.secret, password=None)
            current_time = int(time.time())
            jwt_payload = {
                'sub': self.api_key,
                'iss': 'coinbase-cloud',
                'nbf': current_time,
                'exp': current_time + 120,
                'uri': uri,
            }
            jwt_token = jwt.encode(
                jwt_payload,
                private_key,
                algorithm='ES256',
                headers={'kid': self.api_key, 'nonce': secrets.token_hex()},
            )
        except (jwt.PyJWTError, ValueError) as e:
            raise RemoteError('Error generating JWT token') from e

        return jwt_token

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Coinbase API key is good for usage in rotki.

        For Legacy keys, make sure that the following permissions are given to the key:
        wallet:accounts:read, wallet:transactions:read,
        wallet:withdrawals:read, wallet:deposits:read

        For CDP keys, make sure they are formatted properly
        """
        self.is_legacy_api_key = self.is_legacy_key(self.api_key)
        if self.is_legacy_api_key:
            self.session.headers.update({'CB-ACCESS-KEY': self.api_key, 'CB-VERSION': CB_VERSION})
            result, msg = self._validate_single_api_key_action('accounts')
            if result is None:
                return False, msg

            # now get the account ids
            account_info = self._get_active_account_info(result)
            if len(account_info) != 0:
                # and now try to get all transactions of an account to see if that's possible
                method = f'accounts/{account_info[0][0]}/transactions'
                result, msg = self._validate_single_api_key_action(method)
                if result is None:
                    return False, msg

        else:  # Validate new API key format
            if not NEW_RE.match(self.api_key):
                return False, 'Invalid Coinbase API key name format'

            if not PRIVATE_KEY_RE.match(self.secret.decode('utf-8', 'strict')):
                return False, 'Invalid Coinbase private key format'

        return True, ''

    def _validate_single_api_key_action(
            self,
            method_str: str,
            ignore_pagination: bool = False,
    ) -> tuple[list[Any] | None, str]:
        try:
            result = self._api_query(method_str, ignore_pagination=ignore_pagination)

        except CoinbasePermissionError as e:
            error = str(e)
            if 'transactions' in method_str:
                permission = 'wallet:transactions:read'
            elif 'deposits' in method_str:
                permission = 'wallet:deposits:read'
            elif 'withdrawals' in method_str:
                permission = 'wallet:withdrawals:read'
            elif 'trades' in method_str:
                permission = 'wallet:trades:read'
            # the accounts elif should be at the end since the word appears
            # in other endpoints
            elif 'accounts' in method_str:
                permission = 'wallet:accounts:read'
            else:
                raise AssertionError(
                    f'Unexpected coinbase method {method_str} at API key validation',
                ) from e
            msg = (
                f'Provided Coinbase API key needs to have {permission} permission activated. '
                f'Please log into your coinbase account and set all required permissions: '
                f'wallet:accounts:read, wallet:transactions:read, '
                f'wallet:withdrawals:read, wallet:deposits:read, wallet:trades:read'
            )

            return None, msg
        except RemoteError as e:
            error = str(e)
            if 'invalid signature' in error:
                return None, 'Failed to authenticate with the Provided API key/secret'
            if 'invalid api key' in error:
                return None, 'Provided API Key is invalid'
            # else any other remote error
            return None, error

        return result, ''

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            try:
                new_is_legacy = self.is_legacy_key(credentials.api_key)
            except AuthenticationError as e:
                log.error(f'Invalid coinbase API key format: {e}')
                new_is_legacy = True

            if new_is_legacy != self.is_legacy_api_key:  # Key type has changed
                self.is_legacy_api_key = new_is_legacy

            if self.is_legacy_api_key:
                self.session.headers.update({'CB-ACCESS-KEY': credentials.api_key})
            else:
                self.api_key = credentials.api_key

        return changed

    def _get_active_account_info(self, accounts: list[dict[str, Any]]) -> list[tuple[str, Timestamp]]:  # noqa: E501
        """Gets the account ids and last_update timestamp out of the accounts response

        At the moment of writing this the coinbase API returns the accounts for the assets
        that the user has interacted with and in addition account for BCH, ETH2, BTC and ETH.

        We used to have an activity check comparing the `updated_at` and `created_at` fields
        of the response but in some cases it proved to not be reliable.
        """
        account_info = []
        for account_data in accounts:
            if 'id' not in account_data:
                log.error(
                    'Found coinbase account entry without an id key. Skipping it. ',
                )
                continue

            if not isinstance(account_data['id'], str):
                log.error(
                    f'Found coinbase account entry with a non string id: '
                    f'{account_data["id"]}. Skipping it. ',
                )
                continue

            updated_at = account_data.get('updated_at')
            try:
                timestamp = deserialize_timestamp_from_date(updated_at, 'iso8601', 'coinbase')
            except DeserializationError:
                log.error(f'Skipping coinbase account {account_data} due to inability to deserialize timestamp')  # noqa: E501
                continue

            log.debug(f'Found coinbase account: {account_data}')
            account_info.append((account_data['id'], timestamp))

        return account_info

    def _api_query(
            self,
            endpoint: str,
            options: dict[str, Any] | None = None,
            ignore_pagination: bool = False,
    ) -> list[Any]:
        """Performs a coinbase API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.
        If you want just the first results then set ignore_pagination to True.
        """
        all_items: list[Any] = []
        had_4xx = False
        request_verb = 'GET'
        next_uri = f'/{self.apiversion}/{endpoint}'  # initialize next_uri before loop
        timeout = CachedSettings().get_timeout_tuple()

        if options:
            next_uri += f'?{urlencode(options)}'
        while True:
            if self.is_legacy_api_key:
                timestamp = str(int(time.time()))
                message = timestamp + request_verb + next_uri
                signature = hmac.new(
                    self.secret,
                    message.encode(),
                    hashlib.sha256,
                ).hexdigest()
                self.session.headers.update({
                    'CB-ACCESS-SIGN': signature,
                    'CB-ACCESS-TIMESTAMP': timestamp,
                })

            else:
                uri = f'{request_verb} {self.host}/{self.apiversion}/{endpoint}'
                token = self.build_jwt(uri)
                self.session.headers.update({
                    'Authorization': f'Bearer {token}',
                })

            full_url = self.base_uri + next_uri
            log.debug('Coinbase API query', request_url=full_url)
            try:
                response = self.session.get(full_url, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Coinbase API request failed due to {e!s}') from e

            if response.status_code in (401, 429) and had_4xx is False:
                had_4xx = True
                gevent.sleep(.5)
                continue  # do a single retry since they don't have info on retries

            if response.status_code == 403:
                raise CoinbasePermissionError(f'API key does not have permission for {endpoint}')

            if response.status_code != 200:
                raise RemoteError(
                    f'Coinbase query {full_url} responded with error status code: '
                    f'{response.status_code} and text: {response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'Coinbase returned invalid JSON response: {response.text}',
                ) from e

            if 'data' not in json_ret:
                raise RemoteError(f'Coinbase json response does not contain data: {response.text}')

            all_items.extend(json_ret['data'])  # `data` attr is a list in itself
            if ignore_pagination or 'pagination' not in json_ret:
                # break out of the loop, no need to handle pagination
                break

            if 'next_uri' not in json_ret['pagination']:
                raise RemoteError('Coinbase json response contained no "next_uri" key')

            # otherwise, let the loop run to gather subsequent queries
            # this next_uri will be used in next iteration
            next_uri = json_ret['pagination']['next_uri']
            if not next_uri:
                # As per the docs: https://developers.coinbase.com/api/v2?python#pagination
                # once we get an empty next_uri we are done

                break

        return all_items

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            resp = self._api_query('accounts')
        except RemoteError as e:
            msg_prefix = 'Coinbase API request failed.'
            msg = (
                'Coinbase API request failed. Could not reach coinbase due '
                f'to {e}'
            )
            log.error(f'{msg_prefix} Could not reach coinbase due to {e}')
            return None, f'{msg_prefix} Check logs for more details'

        returned_balances: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for account in resp:
            try:
                if (balance := account.get('balance')) is None:
                    continue

                if (amount_str := balance.get('amount')) is not None:
                    amount = deserialize_fval(amount_str)
                elif (amount_str := balance.get('value')) is not None:
                    amount = deserialize_fval(account['balance']['value'])
                else:  # missing both amount and value
                    log.error(f'Got coinbase account with neither amount, nor value key in balance: {account}')  # noqa: E501
                    continue

                # ignore empty balances. Coinbase returns zero balances for everything
                # a user does not own
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(account['balance']['currency'])
                try:
                    usd_price = Inquirer.find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing coinbase balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except UnsupportedAsset as e:
                log.warning(
                    f'Found coinbase balance result with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                log.error(
                    'Error processing a coinbase account balance',
                    account_balance=account,
                    error=msg,
                )
                continue

        return dict(returned_balances), ''

    @protect_with_lock()
    def _query_transactions(self) -> None:
        """Queries transactions for all active accounts of this coinbase instance

        If an account has been queried within X seconds it's not queried again.
        Accounts are only queried since last known queried event
        """
        account_data = self._api_query('accounts')
        account_info = self._get_active_account_info(account_data)

        now = ts_now()
        self.staking_events = set()
        conversion_pairs: defaultdict[str, list[dict]] = defaultdict(list)
        for account_id, last_update_timestamp in account_info:
            with self.db.conn.read_ctx() as cursor:
                last_query = 0
                if (result := self.db.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_QUERY_TS,
                    location=self.location.serialize(),
                    location_name=self.name,
                    account_id=account_id,
                )) is not None:
                    last_query = result

                if now - last_query < HOUR_IN_SECONDS or last_update_timestamp < last_query:
                    continue  # if no update since last query or last query recent stop

                last_id = None
                if (result_id := self.db.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_QUERY_ID,
                    location=self.location.serialize(),
                    location_name=self.name,
                    account_id=account_id,
                )) is not None:
                    last_id = str(result_id)

            history_events, conversions = self._query_single_account_transactions(
                account_id=account_id,
                account_last_id_name=f'{self.location}_{self.name}_{account_id}_last_query_id',
                last_tx_id=last_id,
            )
            if len(conversion_pairs := combine_dicts(conversion_pairs, conversions)) != 0:
                history_events.extend(self._process_trades_from_conversion(
                    transaction_pairs=conversion_pairs,
                ))

            # The approach here does not follow the exchange interface querying with
            # a different method per type of event. Instead similar to kraken we query
            # all events with 1 api endpoint and save them here. So they are returned
            # directly from the DB later.
            with self.db.user_write() as write_cursor:
                if len(history_events) != 0:
                    db = DBHistoryEvents(self.db)
                    db.add_history_events(write_cursor=write_cursor, history=history_events)
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_QUERY_TS,
                    value=ts_now(),
                    location=self.location.serialize(),
                    location_name=self.name,
                    account_id=account_id,
                )

    def _query_single_account_transactions(
            self,
            account_id: str,
            account_last_id_name: str,
            last_tx_id: str | None,
    ) -> tuple[
            list[HistoryEvent | AssetMovement | SwapEvent],
            defaultdict[str, list[dict]],
        ]:
        """
        Query all the transactions and save all newly generated events

        May raise:
        - RemoteError
        """
        history_events: list[HistoryEvent | AssetMovement | SwapEvent] = []
        options = {}
        if last_tx_id is not None:
            options['starting_after'] = last_tx_id
            options['order'] = 'asc'
        transactions = self._api_query(f'accounts/{account_id}/transactions', options=options)
        transaction_pairs: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)  # Maps every trade id to their two transactions  # noqa: E501
        if len(transactions) == 0:
            log.debug('Coinbase API query returned no transactions')
            return history_events, transaction_pairs

        for transaction in transactions:
            log.debug(f'Processing coinbase {transaction=}')
            tx_type = transaction.get('type')
            if tx_type == 'trade':  # Analyze conversions of coins. We address them as sells
                try:
                    transaction_pairs[transaction['trade']['id']].append(transaction)
                except KeyError:
                    log.error(
                        f'Transaction of type trade doesnt have the '
                        f'expected structure {transaction}',
                    )
            elif tx_type in ('buy', 'sell', 'advanced_trade_fill'):
                history_events.extend(self._process_coinbase_trade(event=transaction))
            elif (
                    tx_type in (
                        'interest', 'inflation_reward', 'staking_reward',
                        'staking_transfer', 'unstaking_transfer', 'cardbuyback',
                        'cardspend', 'incentives_shared_clawback', 'clawback',
                    ) or
                    (
                        tx_type == 'send' and 'from' in transaction and
                        'resource' in transaction['from'] and
                        transaction['from']['resource'] == 'user'
                    )
            ):
                if (history_event := self._deserialize_history_event(transaction)) is not None:
                    history_events.append(history_event)

                    if tx_type in ('staking_transfer', 'unstaking_transfer'):
                        self.staking_events.add((history_event.timestamp, history_event.asset, history_event.amount))  # noqa: E501

            # 'tx' represents uncategorized transactions that don't fit other specific types.
            # Used as fallback when a transaction's nature is unclear.
            # See: https://docs.cdp.coinbase.com/coinbase-app/docs/api-transactions#transaction-types
            elif tx_type in (
                'send', 'fiat_deposit', 'fiat_withdrawal',
                'pro_withdrawal', 'pro_deposit', 'tx',
            ):
                # Their docs don't list all possible types. Added some I saw in the wild
                # and some I assume would exist (exchange_withdrawal, since I saw exchange_deposit)
                if (asset_movement := self._deserialize_asset_movement(transaction)) is not None:
                    history_events.extend(asset_movement)
            elif tx_type not in (
                    'exchange_deposit',  # duplicated from send. Has less info.
                    'exchange_withdrawal',  # assume it exists and has duplicate
            ):
                log.warning(f'Found unknown coinbase transaction type: {transaction}')

        with self.db.user_write() as write_cursor:  # Remember last transaction id for account
            write_cursor.execute(
                'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?) ',
                (account_last_id_name, transactions[-1]['id']),  # -1 takes last transaction due to ascending order  # noqa: E501
            )

        return history_events, transaction_pairs

    def _process_trades_from_conversion(
            self,
            transaction_pairs: dict[str, list],
    ) -> list[SwapEvent]:
        """Processes the transaction pairs to create trades from conversions

        Note: Conversions appear as pairs and each leg of the trade needs to be obtained by
        querying the transactions of the wallets for the involved assets.
        """
        events = []
        for conversion_transactions in transaction_pairs.values():
            tx_1 = conversion_transactions[0]
            tx_2 = None if len(conversion_transactions) == 1 else conversion_transactions[1]

            try:
                events.extend(self._trade_from_conversion(tx_1, tx_2))
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='conversion',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase conversion with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a coinbase conversion. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a coinbase conversion',
                    trade=conversion_transactions[0],
                    error=msg,
                )
                continue

        return events

    def _trade_from_conversion(
            self,
            tx_a: dict[str, Any],
            tx_b: dict[str, Any] | None,
    ) -> list[SwapEvent]:
        """Turn tx information from conversion into a list of SwapEvents.

        Sometimes the amounts can be negative which breaks rotki's logic which is why we use abs().
        Also sometimes there may not be a second transaction, in which case it's a sell for USD
        seen as native_amount of the first transaction.

        May raise:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
        """
        # Check that the status is complete
        if tx_a['status'] != 'completed':
            return []

        # we found cases where trades only had `created_at` so we use that as a fallback.
        timestamp = deserialize_timestamp_from_date(
            date=tx_a.get('updated_at') or tx_a.get('created_at'),
            formatstr='iso8601',
            location='coinbase',
        )
        fee = None
        if tx_b is not None:
            # Trade b will represent the asset we are converting to
            if tx_b['amount']['amount'].startswith('-'):
                tx_a, tx_b = tx_b, tx_a

            tx_amount = abs(deserialize_fval(tx_a['amount']['amount']))
            tx_asset = asset_from_coinbase(tx_a['amount']['currency'], time=timestamp)
            native_amount = abs(deserialize_fval(tx_b['amount']['amount']))
            native_asset = asset_from_coinbase(tx_b['amount']['currency'], time=timestamp)

            amount_after_fee = deserialize_fval(tx_b['native_amount']['amount'])
            amount_before_fee = deserialize_fval(tx_a['native_amount']['amount'])
            if (
                    (fee_a := tx_a['trade'].get('fee')) is not None and
                    (fee_b := tx_b['trade'].get('fee')) is not None and
                    fee_a['amount'] == fee_b['amount']
            ):
                # Lefteris mentioned that conversions for him didn't have at least in the past the
                # fee section. I've kept both of them but we might have to revisit this part of the logic.  # noqa: E501
                # Using the fee field as value for the fee the rate that calculates rotki is correct  # noqa: E501
                # and displays the exact same amounts that the accounting report from coinbase.
                conversion_native_fee_amount = deserialize_fval(
                    value=tx_a['trade']['fee']['amount'],
                    name='conversion fee',
                    location='coinbase conversion',
                )
            else:
                # Obtain fee amount in the native currency using data from both trades
                # amount_after_fee + amount_before_fee is a negative amount and the fee needs to be positive  # noqa: E501
                conversion_native_fee_amount = abs(amount_after_fee + amount_before_fee)

            if ZERO not in {tx_amount, conversion_native_fee_amount, amount_before_fee, amount_after_fee}:  # noqa: E501
                # To get the asset in which the fee is nominated we pay attention to the creation
                # date of each event. As per our hypothesis the fee is nominated in the asset
                # for which the first transaction part was initialized
                time_created_a = deserialize_timestamp_from_date(
                    date=tx_a['created_at'],
                    formatstr='iso8601',
                    location='coinbase',
                )
                time_created_b = deserialize_timestamp_from_date(
                    date=tx_b['created_at'],
                    formatstr='iso8601',
                    location='coinbase',
                )
                if time_created_a < time_created_b:
                    # We have the fee amount in the native currency. To get it in the
                    # converted asset we have to get the rate
                    asset_native_rate = tx_amount / abs(amount_before_fee)
                    fee = AssetAmount(
                        amount=conversion_native_fee_amount * asset_native_rate,
                        asset=asset_from_coinbase(tx_a['amount']['currency'], time=timestamp),
                    )
                else:
                    tx_b_amount = abs(deserialize_fval(tx_b['amount']['amount']))
                    asset_native_rate = tx_b_amount / abs(amount_after_fee)
                    fee = AssetAmount(
                        amount=conversion_native_fee_amount * asset_native_rate,
                        asset=asset_from_coinbase(tx_b['amount']['currency'], time=timestamp),
                    )

        else:  # only one transaction
            tx_amount = abs(deserialize_fval(tx_a['amount']['amount']))
            tx_asset = asset_from_coinbase(tx_a['amount']['currency'], time=timestamp)
            native_amount = abs(deserialize_fval(tx_a['native_amount']['amount']))
            native_asset = asset_from_coinbase(tx_a['native_amount']['currency'], time=timestamp)
            # For a single transaction fee may or may not exist in the transaction.
            if (fee_data := tx_a['trade'].get('fee')) is not None:
                fee = AssetAmount(
                    asset=asset_from_coinbase(fee_data['currency']),
                    amount=abs(deserialize_fval(fee_data['amount'])),
                )

        return create_swap_events(
            timestamp=ts_sec_to_ms(timestamp),
            location=self.location,
            spend=AssetAmount(asset=tx_asset, amount=tx_amount),
            receive=AssetAmount(asset=native_asset, amount=native_amount),
            fee=fee,
            location_label=self.name,
            unique_id=str(tx_a['trade']['id']),
        )

    def _process_coinbase_trade(self, event: dict[str, Any]) -> list[SwapEvent]:
        """Turns a coinbase transaction into a list of SwapEvents and returns it.

        Uses underlying trade processing functions based on the type of trade.
        """
        try:
            if event['status'] != 'completed':
                # We only want to deal with completed trades
                return []

            # Contrary to the Coinbase documentation we will use created_at, and never
            # payout_at. It seems like payout_at is not actually the time when the
            # trade is settled. Reports generated by Coinbase use created_at as well
            if event.get('created_at') is not None:
                raw_time = event['created_at']
            else:
                raw_time = event['payout_at']

            timestamp = deserialize_timestamp_from_date(raw_time, 'iso8601', 'coinbase')

            if event['type'] in ('buy', 'sell'):
                return self._process_normal_trade(event, timestamp)
            elif event['type'] == 'advanced_trade_fill':
                return self._process_advanced_trade(event, timestamp)

        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='transaction',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase trade with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError, IndexError, ZeroDivisionError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Error processing a coinbase trade. Check logs '
                'for details. Ignoring it.',
            )
            log.error(
                'Error processing a coinbase trade',
                trade=event,
                error=msg,
            )

        return []

    def _process_normal_trade(
            self,
            event: dict[str, Any],
            timestamp: Timestamp,
    ) -> list[SwapEvent]:
        """Turns a normal coinbase transaction into a list of SwapEvents and returns it.

        Sometimes the amounts can be negative which breaks rotki's logic which is why we use abs().

        https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-transactions#transaction-types
        If the coinbase transaction is not a trade related transaction nothing happens.

        May raise:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
        - ZeroDivisionError due to rate calculation
        """
        tx_amount = deserialize_fval_force_positive(event['amount']['amount'])
        tx_asset = asset_from_coinbase(event['amount']['currency'], time=timestamp)
        native_amount = deserialize_fval_force_positive(event['native_amount']['amount'])
        native_asset = asset_from_coinbase(event['native_amount']['currency'], time=timestamp)
        spend_asset, spend_amount, receive_asset, receive_amount = (
            (native_asset, native_amount, tx_asset, tx_amount)
            if event['type'] == 'buy' else  # Either buy or sell in _process_normal_trade
            (tx_asset, tx_amount, native_asset, native_amount)
        )
        return create_swap_events(
            timestamp=ts_sec_to_ms(timestamp),
            location=self.location,
            spend=AssetAmount(asset=spend_asset, amount=spend_amount),
            receive=AssetAmount(asset=receive_asset, amount=receive_amount),
            fee=AssetAmount(
                amount=abs(deserialize_fval_or_zero(event['fee']['amount'])),
                asset=asset_from_coinbase(event['fee']['currency'], time=timestamp),
            ) if 'fee' in event else None,
            location_label=self.name,
            unique_id=str(event['id']),
        )

    def _process_advanced_trade(
            self,
            event: dict[str, Any],
            timestamp: Timestamp,
    ) -> list[SwapEvent]:
        """Turns an advanced_trade_fill transaction into a list of SwapEvents and returns it.

        https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-transactions#transaction-types
        If the coinbase transaction is not a trade related transaction nothing happens.

        Trades against USD can also be missing (but not necessarily do) the order_side key.

        May raise:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
        - IndexError due to indices being out of bounds when parsing asset ids
        """
        # Notice that we do not use abs() yet, since this helps determine order type down the line
        amount = deserialize_fval(event['amount']['amount'])
        tx_asset = asset_from_coinbase(event['amount']['currency'], time=timestamp)
        if len(asset_identifiers := event['advanced_trade_fill']['product_id'].split('-')) != 2:
            log.error('Error processing asset identifiers for coinbase trade', trade=event)
            return []

        if (order_side := event['advanced_trade_fill'].get('order_side')) is None:
            order_side = 'buy' if amount < 0 else 'sell'
        elif (
            (order_id := event['advanced_trade_fill'].get('order_id')) is not None and
            (event_currency := event['amount'].get('currency')) is not None
        ):
            if (existing_trade_currency := self.advanced_orders_to_currency.get(order_id)) is None:
                self.advanced_orders_to_currency[order_id] = event_currency
            elif existing_trade_currency != event_currency:
                log.debug('Ignoring other side of already seen coinbase advanced trade', other_side=event)  # noqa: E501
                return []

        # The base/quote asset is determined from the product id
        quote_asset = asset_from_coinbase(asset_identifiers[1], time=timestamp)
        rate = Price(deserialize_fval(event['advanced_trade_fill']['fill_price'], name='fill_price', location='Coinbase advanced trade'))  # noqa: E501
        if tx_asset == quote_asset:  # calculate trade amount depending on the denominated asset
            amount /= rate

        spend, receive = get_swap_spend_receive(
            is_buy=deserialize_trade_type_is_buy(order_side),
            base_asset=asset_from_coinbase(asset_identifiers[0], time=timestamp),
            quote_asset=quote_asset,
            amount=abs(amount),
            rate=rate,
        )
        return create_swap_events(
            timestamp=ts_sec_to_ms(timestamp),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=quote_asset,  # fee is always in quote asset
                amount=abs(deserialize_fval_or_zero(event['advanced_trade_fill']['commission'])),
            ),
            location_label=self.name,
            unique_id=str(event['id']),
        )

    def _deserialize_asset_movement(self, raw_data: dict[str, Any]) -> list[AssetMovement] | None:
        """Processes a single deposit/withdrawal from coinbase and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data.get('status') != 'completed':
                return None

            payout_date = raw_data.get('payout_at')
            if payout_date:
                timestamp = deserialize_timestamp_from_date(payout_date, 'iso8601', 'coinbase')
            else:
                timestamp = deserialize_timestamp_from_date(
                    get_key_if_has_val(raw_data, 'created_at'),
                    'iso8601',
                    'coinbase',
                )

            # Only get address/transaction id for "send" type of transactions
            address = None
            transaction_id, transaction_hash = raw_data.get('id'), None
            notes, fee = None, None
            tx_type = raw_data['type']  # not sure if fiat
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
            amount_data = raw_data['amount']
            # 'pro_deposit' is treated as withdrawal since it debits funds from Coinbase
            # See: https://docs.cdp.coinbase.com/coinbase-app/docs/api-transactions#parameters
            if tx_type == 'fiat_withdrawal':
                event_type = HistoryEventType.WITHDRAWAL
            elif tx_type == 'pro_deposit':
                notes = 'Transfer funds to CoinbasePro'
                event_type = HistoryEventType.WITHDRAWAL
            elif tx_type in ('send', 'tx'):
                event_type = HistoryEventType.WITHDRAWAL if amount_data['amount'].startswith('-') else HistoryEventType.DEPOSIT  # noqa: E501
            elif tx_type == 'fiat_deposit':
                event_type = HistoryEventType.DEPOSIT
            elif tx_type == 'pro_withdrawal':
                event_type = HistoryEventType.DEPOSIT
                notes = 'Transfer funds from CoinbasePro'
            else:
                log.error(
                    f'In a coinbase deposit/withdrawal we got unknown type {tx_type}',
                )
                return None

            # Can't see the fee being charged from the "send" resource
            amount = deserialize_fval_force_positive(amount_data['amount'])
            asset = asset_from_coinbase(amount_data['currency'], time=timestamp)
            # Fees dont appear in the docs but from an experiment of sending ETH
            # to an address from coinbase there is the network fee in the response
            raw_network = raw_data.get('network', {})
            if raw_network and 'transaction_fee' in raw_network:
                raw_fee = raw_network['transaction_fee']
                if raw_fee:
                    fee_asset = raw_fee['currency']
                    # Since this is a withdrawal the fee should be the same as the moved asset
                    if asset != asset_from_coinbase(fee_asset, time=timestamp):
                        # If not we set ZERO fee and ignore
                        log.error(
                            f'In a coinbase withdrawal of {asset.identifier} the fee'
                            f'is denoted in {raw_fee["currency"]}',
                        )
                    else:
                        fee = AssetAmount(
                            asset=asset,
                            amount=deserialize_fval_or_zero(raw_fee['amount']),
                        )
                        amount -= fee.amount  # fee is deducted from withdrawal amount

            if 'network' in raw_data:
                transaction_hash = get_key_if_has_val(raw_data['network'], 'hash')

            raw_to = raw_data.get('to')
            if raw_to is not None:
                address = deserialize_asset_movement_address(raw_to, 'address', asset)

            if 'to' in raw_data and raw_to is None:  # Internal movement between coinbase accs
                return None  # Can ignore. https://github.com/rotki/rotki/issues/3901

            if 'from' in raw_data:
                event_type = HistoryEventType.DEPOSIT

        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='deposit/withdrawal',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase deposit/withdrawal with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a coinbase '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of coinbase '
                f'asset_movement {raw_data}. Error was: {msg}',
            )
        else:
            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_type=event_type,
                timestamp=ts_sec_to_ms(timestamp),
                asset=asset,
                amount=amount,
                fee=fee,
                unique_id=transaction_id,
                extra_data=maybe_set_transaction_extra_data(
                    address=address,
                    transaction_id=transaction_hash,
                    extra_data={'reference': transaction_id} if transaction_id is not None else None,  # noqa: E501
                ),
                movement_notes=notes,
            )

        return None

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Make sure latest transactions are queried and saved in the DB. Since all history comes from one endpoint and can't be queried by time range this doesn't follow the same logic as another exchanges"""  # noqa: E501
        self._query_transactions()
        return [], end_ts

    def _deserialize_history_event(self, raw_data: dict[str, Any]) -> HistoryEvent | None:
        """Processes a single transaction from coinbase and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data.get('status') != 'completed':
                return None
            payout_date = raw_data.get('payout_at')
            if payout_date:
                timestamp = deserialize_timestamp_from_date(payout_date, 'iso8601', 'coinbase')
            else:
                timestamp = deserialize_timestamp_from_date(
                    get_key_if_has_val(raw_data, 'created_at'),
                    'iso8601',
                    'coinbase',
                )

            amount_data = raw_data.get('amount', {})
            amount = deserialize_fval_force_positive(amount_data['amount'])
            asset = asset_from_coinbase(amount_data['currency'], time=timestamp)
            notes = raw_data.get('details', {}).get('header', '')
            tx_type = raw_data['type']
            event_identifier = f'{CB_EVENTS_PREFIX}{raw_data["id"]!s}'
            timestamp_ms = ts_sec_to_ms(timestamp)
            if notes != '':
                notes += f' {"from coinbase earn" if tx_type == "send" else "as " + tx_type}'

            if tx_type in ('staking_transfer', 'unstaking_transfer'):
                # Staking transfers appear twice (in the normal & staking accounts), so skip if
                # we've already seen a similar event (amounts match since we force positive above).
                if (timestamp_ms, asset, amount) in self.staking_events:
                    return None

                event_type = HistoryEventType.STAKING
                if tx_type == 'staking_transfer':
                    event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    verb = 'Stake'
                else:
                    event_subtype = HistoryEventSubType.REMOVE_ASSET
                    verb = 'Unstake'

                notes = f'{verb} {amount} {asset.symbol_or_name()} in Coinbase'
            elif tx_type == 'staking_reward':
                event_type = HistoryEventType.STAKING
                event_subtype = HistoryEventSubType.REWARD
                notes = f'Receive {amount} {asset.symbol_or_name()} as Coinbase staking reward'
            elif tx_type in ('incentives_shared_clawback', 'clawback'):
                event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.CLAWBACK
                notes = f'Coinbase clawback of {amount} {asset.symbol_or_name()}'
            elif tx_type == 'cardspend':
                event_type, event_subtype = HistoryEventType.SPEND, HistoryEventSubType.PAYMENT
                notes = f'Spend {amount} {asset.symbol_or_name()} via Coinbase card'
            elif tx_type == 'cardbuyback':
                event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.CASHBACK
                notes = f'Receive cashback of {amount} {asset.symbol_or_name()} from Coinbase'
            else:
                event_type, event_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.NONE

            return HistoryEvent(
                event_identifier=event_identifier,
                sequence_index=0,
                timestamp=timestamp_ms,
                location=Location.COINBASE,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                amount=amount,
                location_label=self.name,
                notes=notes,
            )

        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='transaction',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase transaction with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a coinbase '
                'history event. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of coinbase '
                f'history event {raw_data}. Error was: {msg}',
            )
        return None

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for coinbase
