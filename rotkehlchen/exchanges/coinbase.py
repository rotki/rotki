import hashlib
import hmac
import logging
import time
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    ExchangeAuthCredentials,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CB_EVENTS_PREFIX = 'CBE_'
CB_VERSION = '2019-08-25'  # the latest api version we know rotki works fine for: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/versioning  # noqa: E501


def trade_from_conversion(trade_a: dict[str, Any], trade_b: dict[str, Any]) -> Trade | None:
    """Turn information from a conversion into a trade

    Mary raise:
    - UnknownAsset due to Asset instantiation
    - DeserializationError due to unexpected format of dict entries
    - KeyError due to dict entries missing an expected entry
    """
    # Check that the status is complete
    if trade_a['status'] != 'completed':
        return None

    # Trade b will represent the asset we are converting to
    if trade_b['amount']['amount'].startswith('-'):
        trade_a, trade_b = trade_b, trade_a

    timestamp = deserialize_timestamp_from_date(trade_a['updated_at'], 'iso8601', 'coinbase')
    tx_amount = AssetAmount(abs(deserialize_asset_amount(trade_a['amount']['amount'])))
    tx_asset = asset_from_coinbase(trade_a['amount']['currency'], time=timestamp)
    native_amount = deserialize_asset_amount(trade_b['amount']['amount'])
    native_asset = asset_from_coinbase(trade_b['amount']['currency'], time=timestamp)
    amount = tx_amount
    # The rate is how much you get/give in quotecurrency if you buy/sell 1 unit of base currency
    rate = Price(native_amount / tx_amount)

    # Obtain fee amount in the native currency using data from both trades
    amount_after_fee = deserialize_asset_amount(trade_b['native_amount']['amount'])
    amount_before_fee = deserialize_asset_amount(trade_a['native_amount']['amount'])
    # amount_after_fee + amount_before_fee is a negative amount and the fee needs to be positive
    conversion_native_fee_amount = abs(amount_after_fee + amount_before_fee)
    if ZERO not in {tx_amount, conversion_native_fee_amount, amount_before_fee, amount_after_fee}:
        # To get the asset in which the fee is nominated we pay attention to the creation
        # date of each event. As per our hypothesis the fee is nominated in the asset
        # for which the first transaction part was initialized
        time_created_a = deserialize_timestamp_from_date(
            date=trade_a['created_at'],
            formatstr='iso8601',
            location='coinbase',
        )
        time_created_b = deserialize_timestamp_from_date(
            date=trade_b['created_at'],
            formatstr='iso8601',
            location='coinbase',
        )
        if time_created_a < time_created_b:
            # We have the fee amount in the native currency. To get it in the
            # converted asset we have to get the rate
            asset_native_rate = tx_amount / abs(amount_before_fee)
            fee_amount = Fee(conversion_native_fee_amount * asset_native_rate)
            fee_asset = asset_from_coinbase(trade_a['amount']['currency'], time=timestamp)
        else:
            trade_b_amount = abs(deserialize_asset_amount(trade_b['amount']['amount']))
            asset_native_rate = trade_b_amount / abs(amount_after_fee)
            fee_amount = Fee(conversion_native_fee_amount * asset_native_rate)
            fee_asset = asset_from_coinbase(trade_b['amount']['currency'], time=timestamp)
    else:
        fee_amount = Fee(ZERO)
        fee_asset = asset_from_coinbase(trade_a['amount']['currency'], time=timestamp)

    return Trade(
        timestamp=timestamp,
        location=Location.COINBASE,
        # in coinbase you are buying/selling tx_asset for native_asset
        base_asset=tx_asset,
        quote_asset=native_asset,
        trade_type=TradeType.SELL,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(trade_a['trade']['id']),
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
        )
        self.apiversion = 'v2'
        self.base_uri = 'https://api.coinbase.com'
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({'CB-ACCESS-KEY': self.api_key})
        self.session.headers.update({'CB-VERSION': CB_VERSION})

    def first_connection(self) -> None:
        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'CB-ACCESS-KEY': self.api_key})
        return changed

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

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Coinbase API key is good for usage in rotki

        Makes sure that the following permissions are given to the key:
        wallet:accounts:read, wallet:transactions:read,
        wallet:withdrawals:read, wallet:deposits:read
        """
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

        return True, ''

    def _get_active_account_info(self, accounts: list[dict[str, Any]]) -> list[tuple[str, Timestamp]]:  # noqa: E501
        """Gets the account ids and last_update timestamp out of the accounts response

        Only returns the active ones. We assume that if created_at and updated_at are
        the same then the account is not active. This is important as the API requires
        iteration over all accounts to get history and there is A LOT of them.
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
            if account_data.get('created_at') == updated_at:
                continue  # assume no activity

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
        # initialize next_uri before loop
        next_uri = f'/{self.apiversion}/{endpoint}'
        timeout = CachedSettings().get_timeout_tuple()
        if options:
            next_uri += urlencode(options)
        while True:
            timestamp = str(int(time.time()))
            message = timestamp + request_verb + next_uri

            signature = hmac.new(
                self.secret,
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
            log.debug('Coinbase API query', request_url=next_uri)

            self.session.headers.update({
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
            })

            full_url = self.base_uri + next_uri
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

            # `data` attr is a list in itself
            all_items.extend(json_ret['data'])
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
                    amount = deserialize_asset_amount(amount_str)
                elif (amount_str := balance.get('value')) is not None:
                    amount = deserialize_asset_amount(account['balance']['value'])
                else:  # missing both amount and value
                    log.error(f'Got coinbase account with neither amount, nor value key in balance: {account}')  # noqa: E501
                    continue

                # ignore empty balances. Coinbase returns zero balances for everything
                # a user does not own
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(account['balance']['currency'])
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
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
                log.warning(
                    f'Found coinbase balance result with unknown asset '
                    f'{e.identifier}. Ignoring it.',
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
        for account_id, last_update_timestamp in account_info:
            # TODO: The used query range should be replaced by cache for this: https://github.com/rotki/rotki/issues/5684  # noqa: E501
            account_last_ts_name = f'{self.location}_{self.name}_{account_id}_last_query_ts'
            with self.db.conn.read_ctx() as cursor:
                cursor.execute('SELECT end_ts FROM used_query_ranges WHERE name=?', (account_last_ts_name,))  # noqa: E501
                last_query = 0
                if (result := cursor.fetchone()) is not None:
                    last_query = result[0]

                if now - last_query < HOUR_IN_SECONDS or last_update_timestamp < last_query:
                    continue  # if no update since last query or last query recent stop

                account_last_id_name = f'{self.location}_{self.name}_{account_id}_last_query_id'
                cursor.execute('SELECT end_ts FROM used_query_ranges WHERE name=?', (account_last_id_name,))  # TODO: change this too for 5684  # noqa: E501
                last_id = None
                if (result := cursor.fetchone()) is not None:
                    last_id = result[0]

            trades, asset_movements, history_events = self._query_single_account_transactions(
                account_id=account_id,
                account_last_id_name=account_last_id_name,
                last_tx_id=last_id,
            )

            # The approach here does not follow the exchange interface querying with
            # a different method per type of event. Instead similar to kraken we query
            # all events with 1 api endpoint and save them here. So they are returned
            # directly from the DB later.
            with self.db.user_write() as write_cursor:
                if len(trades) != 0:
                    self.db.add_trades(write_cursor=write_cursor, trades=trades)
                if len(asset_movements) != 0:
                    self.db.add_asset_movements(write_cursor=write_cursor, asset_movements=asset_movements)  # noqa: E501
                if len(history_events) != 0:
                    db = DBHistoryEvents(self.db)
                    db.add_history_events(write_cursor=write_cursor, history=history_events)
                write_cursor.execute(  # TODO: Replace with cache from 5684 like above
                    'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES(?, ?, ?) ',  # noqa: E501
                    (account_last_ts_name, 0, ts_now()),
                )

    def _query_single_account_transactions(
            self,
            account_id: str,
            account_last_id_name: str,
            last_tx_id: str | None,
    ) -> tuple[list[Trade], list[AssetMovement], list[HistoryEvent]]:
        """
        Query all the transactions and save all newly generated events

        May raise:
        - RemoteError
        """
        trades: list[Trade] = []
        asset_movements: list[AssetMovement] = []
        history_events: list[HistoryEvent] = []
        options = {}
        if last_tx_id is not None:
            options['starting_after'] = last_tx_id
        transactions = self._api_query(f'accounts/{account_id}/transactions', options=options)
        if len(transactions) == 0:
            return trades, asset_movements, history_events

        trade_pairs = defaultdict(list)  # Maps every trade id to their two transactions
        trades = []
        asset_movements = []
        for transaction in transactions:
            log.debug(f'Processing coinbase {transaction=}')
            tx_type = transaction.get('type')
            if tx_type == 'trade':  # Analyze conversions of coins. We address them as sells
                try:
                    trade_pairs[transaction['trade']['id']].append(transaction)
                except KeyError:
                    log.error(
                        f'Transaction of type trade doesnt have the '
                        f'expected structure {transaction}',
                    )
            elif tx_type in ('buy', 'sell'):
                self._process_normal_trade(event=transaction, trades=trades)
            elif (
                    tx_type in ('interest', 'inflation_reward') or
                    (
                        tx_type == 'send' and 'from' in transaction and
                        'resource' in transaction['from'] and
                        transaction['from']['resource'] == 'user'
                    )
            ):
                if (history_event := self._deserialize_history_event(transaction)) is not None:
                    history_events.append(history_event)
            elif tx_type in ('send', 'fiat_deposit', 'fiat_withdrawal', 'pro_withdrawal'):
                # Their docs don't list all possible types. Added some I saw in the wild
                # and some I assume would exist (exchange_withdrawal, since I saw exchange_deposit)
                if (asset_movement := self._deserialize_asset_movement(transaction)) is not None:
                    asset_movements.append(asset_movement)
            elif tx_type not in (
                    'exchange_deposit',  # duplicated from send. Has less info.
                    'exchange_withdrawal',  # assume it exists and has duplicate
            ):
                log.warning(f'Found unknown coinbase transaction type: {transaction}')

        self._process_trades_from_conversion(trade_pairs=trade_pairs, trades=trades)

        with self.db.user_write() as write_cursor:  # Remember last transaction id for account
            write_cursor.execute(  # TODO: Replace with cache from 5684 like above
                'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES(?, ?, ?) ',  # noqa: E501
                (account_last_id_name, 0, transactions[-1]['id']),
            )

        return trades, asset_movements, history_events

    def _process_trades_from_conversion(self, trade_pairs: dict[str, list], trades: list[Trade]) -> None:  # noqa: E501
        """Processes the trade pairs to create trades from conversions"""
        for trade_id, trades_conversion in trade_pairs.items():
            # Assert that in fact we have two trades
            if len(trades_conversion) != 2:
                log.error(
                    f'Conversion with id {trade_id} doesnt '
                    f'have two transactions. {trades_conversion}',
                )
                continue

            try:
                if (trade := trade_from_conversion(trades_conversion[0], trades_conversion[1])) is not None:  # noqa: E501
                    trades.append(trade)

            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase conversion with unknown asset '
                    f'{e.identifier}. Ignoring it.',
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
                    trade=trades_conversion[0],
                    error=msg,
                )
                continue

    def _process_normal_trade(self, event: dict[str, Any], trades: list[Trade]) -> None:
        """Turns a coinbase transaction into a rotki trade and adds it to the list.

        https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-transactions#transaction-types
        If the coinbase transaction is not a trade related transaction nothing happens.
        """
        try:
            if event['status'] != 'completed':
                # We only want to deal with completed trades
                return None

            # Contrary to the Coinbase documentation we will use created_at, and never
            # payout_at. It seems like payout_at is not actually the time when the
            # trade is settled. Reports generated by Coinbase use created_at as well
            if event.get('created_at') is not None:
                raw_time = event['created_at']
            else:
                raw_time = event['payout_at']

            timestamp = deserialize_timestamp_from_date(raw_time, 'iso8601', 'coinbase')
            trade_type = TradeType.deserialize(event['type'])
            amount = AssetAmount(abs(deserialize_asset_amount(event['amount']['amount'])))
            tx_asset = asset_from_coinbase(event['amount']['currency'], time=timestamp)
            native_amount = deserialize_asset_amount(event['native_amount']['amount'])
            native_asset = asset_from_coinbase(event['native_amount']['currency'], time=timestamp)
            # rate is how much you get/give in quotecurrency if you buy/sell 1 unit of basecurrency
            rate = Price(native_amount / amount)

            fee_amount = fee_asset = None
            if 'fee' in event:
                fee_amount = deserialize_fee(event['fee']['amount'])
                fee_asset = asset_from_coinbase(event['fee']['currency'], time=timestamp)

            trades.append(Trade(
                timestamp=timestamp,
                location=Location.COINBASE,
                # in coinbase you are buying/selling tx_asset for native_asset
                base_asset=tx_asset,
                quote_asset=native_asset,
                trade_type=trade_type,
                amount=amount,
                rate=rate,
                fee=fee_amount,
                fee_currency=fee_asset,
                link=str(event['id']),
            ))
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase transaction with unknown asset '
                f'{e.identifier}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase trade with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
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

        return None

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
        """Make sure latest transactions are queried and saved in the DB. Since all history comes from one endpoint and can't be queried by time range this doesn't follow the same logic as other exchanges"""  # noqa: E501
        self._query_transactions()
        return [], (start_ts, end_ts)

    def _deserialize_asset_movement(self, raw_data: dict[str, Any]) -> AssetMovement | None:
        """Processes a single deposit/withdrawal from coinbase and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data.get('status') != 'completed':
                return None

            payout_date = raw_data.get('payout_at', None)
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
            transaction_id = None
            transaction_url = raw_data.get('id', '')
            fee = Fee(ZERO)
            tx_type = raw_data['type']  # not sure if fiat
            if tx_type in ('send', 'fiat_withdrawal'):
                movement_category = AssetMovementCategory.WITHDRAWAL
            elif tx_type in ('fiat_deposit', 'pro_withdrawal'):
                movement_category = AssetMovementCategory.DEPOSIT
                if tx_type == 'pro_withdrawal':
                    transaction_id = 'From Coinbase Pro'
            else:
                log.error(
                    f'In a coinbase deposit/withdrawal we got unknown type {tx_type}',
                )
                return None

            # Can't see the fee being charged from the "send" resource
            amount_data = raw_data.get('amount', {})
            amount = deserialize_asset_amount_force_positive(amount_data['amount'])
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
                        fee = deserialize_fee(raw_fee['amount'])

            if 'network' in raw_data:
                transaction_id = get_key_if_has_val(raw_data['network'], 'hash')
                transaction_url = get_key_if_has_val(raw_data['network'], 'transaction_url')
            raw_to = raw_data.get('to')
            if raw_to is not None:
                address = deserialize_asset_movement_address(raw_to, 'address', asset)

            if 'to' in raw_data and raw_to is None:  # Internal movement between coinbase accs
                return None  # Can ignore. https://github.com/rotki/rotki/issues/3901

            if 'from' in raw_data:
                movement_category = AssetMovementCategory.DEPOSIT

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase deposit/withdrawal with unknown asset '
                f'{e.identifier}. Ignoring it.',
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
            return AssetMovement(
                location=Location.COINBASE,
                category=movement_category,
                address=address,
                transaction_id=transaction_id,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                fee=fee,
                link=str(transaction_url),
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Make sure latest transactions are queried and saved in the DB. Since all history comes from one endpoint and can't be queried by time range this doesn't follow the same logic as aother exchanges"""  # noqa: E501
        self._query_transactions()
        return []

    def query_online_income_loss_expense(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[HistoryEvent]:
        """Make sure latest transactions are queried and saved in the DB. Since all history comes from one endpoint and can't be queried by time range this doesn't follow the same logic as aother exchanges"""  # noqa: E501
        self._query_transactions()
        return []

    def _deserialize_history_event(self, raw_data: dict[str, Any]) -> HistoryEvent | None:
        """Processes a single transaction from coinbase and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data.get('status') != 'completed':
                return None
            payout_date = raw_data.get('payout_at', None)
            if payout_date:
                timestamp = deserialize_timestamp_from_date(payout_date, 'iso8601', 'coinbase')
            else:
                timestamp = deserialize_timestamp_from_date(
                    get_key_if_has_val(raw_data, 'created_at'),
                    'iso8601',
                    'coinbase',
                )

            amount_data = raw_data.get('amount', {})
            amount = deserialize_asset_amount(amount_data['amount'])
            asset = asset_from_coinbase(amount_data['currency'], time=timestamp)
            notes = raw_data.get('details', {}).get('header', '')
            tx_type = raw_data['type']
            if notes != '':
                notes += f' {"from coinbase earn" if tx_type == "send" else "as " + tx_type}'
            return HistoryEvent(
                event_identifier=f'{CB_EVENTS_PREFIX}{raw_data["id"]!s}',
                sequence_index=0,
                timestamp=ts_sec_to_ms(timestamp),
                location=Location.COINBASE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=asset,
                balance=Balance(amount=amount, usd_value=ZERO),
                location_label=None,
                notes=notes,
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found coinbase transaction with unknown asset '
                f'{e.identifier}. Ignoring it.',
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
