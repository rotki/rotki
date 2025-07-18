import json
import logging
import urllib.parse
from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bybit
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.globaldb.handler import GlobalDBHandler
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
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
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
from rotkehlchen.utils.misc import combine_dicts, ts_ms_to_sec, ts_now, ts_now_in_ms, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator


PAGINATION_LIMIT: Final = 50
# RECEIVE_WINDOW specifies how long an HTTP request is valid.
# It is also used to prevent replay attacks. its unit in ms
# https://bybit-exchange.github.io/docs/v5/guide#parameters-for-authenticated-endpoints
RECEIVE_WINDOW: Final = '10000'
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def bybit_symbol_to_base_quote(
        symbol: str,
        four_letter_assets: set[str],
) -> tuple[AssetWithOracles, AssetWithOracles]:
    """Turns a bybit symbol product into a base/quote asset tuple

    - Can raise UnknownAsset if any of the pair assets are not known to rotki
    """
    # bybit has special pairs with perpetuals/shorts of the tokens
    split_symbol = None
    if '2L' in symbol:
        split_symbol = symbol.split('2L')
    elif '2S' in symbol:
        split_symbol = symbol.split('2S')
    elif '3L' in symbol:
        split_symbol = symbol.split('3L')
    elif '3S' in symbol:
        split_symbol = symbol.split('3S')
    elif '2' in symbol:
        split_symbol = symbol.split('2')

    if split_symbol is not None and len(split_symbol) == 2:
        base_asset = asset_from_bybit(split_symbol[0])
        quote_asset = asset_from_bybit(split_symbol[1])
    elif len(symbol) >= 4 and symbol[-4:] in four_letter_assets:
        base_asset, quote_asset = asset_from_bybit(symbol[:-4].upper()), asset_from_bybit(symbol[-4:].upper())  # noqa: E501
    else:
        base_asset, quote_asset = asset_from_bybit(symbol[:-3].upper()), asset_from_bybit(symbol[-3:].upper())  # noqa: E501

    return base_asset, quote_asset


class Bybit(ExchangeInterface, SignatureGeneratorMixin):
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ):
        """
        Interact with the bybit API.

        Bybit has support for two types of accounts: classic and unified. At some point in time
        bybit introduced the unified account type and accounts created before that time and didn't
        upgrade are of the classic type. The account type affects the endpoints that can be
        queried and the arguments used in api calls. We extract this information from the API key
        information endpoint when calling `first_connection`.
        """
        super().__init__(
            name=name,
            location=Location.BYBIT,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://api.bybit.com/v5'
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-RECV-WINDOW': RECEIVE_WINDOW,
            'X-BAPI-API-KEY': self.api_key,
        })
        self.authenticated_methods = {
            'account/wallet-balance',
            'account/transaction-log',
            'order/history',
            'user/query-api',
            'asset/deposit/query-record',
            'asset/withdraw/query-record',
            'asset/transfer/query-account-coins-balance',
        }
        self.is_unified_account = False
        self.history_events_db = DBHistoryEvents(self.db)
        self.four_letter_assets = {'USDT', 'USDC', 'USDE', 'USDQ', 'USDR'}  # known quote assets
        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT exchange_symbol FROM location_asset_mappings WHERE (location IS ? OR location IS NULL) AND LENGTH(exchange_symbol) = 4;',  # noqa: E501
                (Location.BYBIT.serialize_for_db(),),
            )
            for symbol in cursor:
                self.four_letter_assets.add(symbol[0])

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if changed is True:
            self.session.headers.update({'X-BAPI-API-KEY': self.api_key})

        return changed

    def first_connection(self) -> None:
        if self.first_connection_made is True:
            return

        try:
            result = self._api_query(path='user/query-api')
        except RemoteError as e:
            log.error(f'Could not get api key information at connection for bybit due to {e}')
            return

        try:
            self.is_unified_account = result['uta'] == 1
        except KeyError:
            log.error('Failed to read uta value from first connection due to key error')
            return

        self.first_connection_made = True

    def _api_query(
            self,
            path: Literal[
                'account/wallet-balance',
                'account/transaction-log',
                'order/history',
                'user/query-api',
                'asset/deposit/query-record',
                'asset/withdraw/query-record',
                'asset/transfer/query-account-coins-balance',
                'market/tickers',
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
        headers = None

        while True:
            log.debug('Bybit API Query', url=url, options=options)
            if requires_auth:
                timestamp = ts_now_in_ms()
                # the order in this string is defined by the api
                param_str = str(timestamp) + self.api_key + RECEIVE_WINDOW
                if options is not None:
                    options = dict(sorted(options.items()))
                    param_str += '&'.join(  # params need to be sorted to be correctly validated
                        [
                            str(k) + '=' + urllib.parse.quote_plus(str(v))  # need to use the quoted string since cursors have `=` and it breaks signatures  # noqa: E501
                            for k, v in sorted(options.items())
                            if v is not None
                        ],
                    )

                signature = self.generate_hmac_signature(param_str)
                headers = {
                    'X-BAPI-TIMESTAMP': str(timestamp),
                    'X-BAPI-SIGN': signature,
                }

            try:
                response = self.session.request(
                    method='get',
                    url=url,
                    params=options,
                    timeout=timeout,
                    headers=headers,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Bybit API request failed due to {e}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if tries >= 1:
                    backoff_seconds = 10 / tries
                    log.debug(f'Got a 429 from Bybit. Backing off for {backoff_seconds}')
                    gevent.sleep(backoff_seconds)
                    tries -= 1
                    continue

                # else
                raise RemoteError(
                    f'Bybit api request for {response.url} failed with HTTP '
                    f'status code {response.status_code} and response {response.text}',
                )

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'Bybit api request for {response.url} failed with HTTP status '
                    f'code {response.status_code} and response {response.text}',
                )

            break  # else all good, we can break off the retry loop

        log.debug(f'ByBit api response: {response.text}')
        try:
            json_ret: dict[str, Any] = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RemoteError('Bybit returned invalid JSON response') from e

        if (result := json_ret.get('result')) is None:
            raise RemoteError(f'Remote response is missing expected field result: {json_ret}')

        if json_ret.get('retCode', 0) != 0 and json_ret.get('retMsg', 'OK') != 'OK':
            raise RemoteError(f'Bybit returned error in request {json_ret}')

        return result

    def _paginated_api_query(
            self,
            endpoint: Literal[
                'order/history',
                'asset/deposit/query-record',
                'asset/withdraw/query-record',
            ],
            options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Query endpoints that can return paginated data. At the moment this is used for asset
        movements and trades. We follow a different approach in each case. For asset movements
        we use cursor pagination since for any time range the api will return a valid response
        and we don't know when to stop querying. The cursor pagination uses the id of the last
        object in the last query to return the results of the next page.

        In the case of trades we query using the endTs/startTs since we can query up to two years
        in the past and this allows us more granularity if we need to query time periods since we
        don't need to skip objects until we reach the desired range.
        """
        if endpoint == 'order/history':
            result_key = 'list'
        else:
            result_key = 'rows'

        result = []
        # copy since we are modifying the dict and could affect other queries using
        # the same options
        query_options = options.copy()
        while True:
            output = self._api_query(path=endpoint, options=query_options)
            if (next_cursor := output.get('nextPageCursor')) is not None and len(next_cursor) != 0:
                query_options['cursor'] = next_cursor

            result.extend(output[result_key])
            if len(output[result_key]) < query_options.get(result_key, PAGINATION_LIMIT):
                break

        return result

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """
        Query trades from bybit in the spot category.
        The API is limited to query trades up to two years into the past. We can query time ranges
        but we don't know when to stop querying into the past. What this function does is iterate
        over the 2 years period moving the queried frame in the maximum allowed time span, that is
        one week:
        [start_ts, start_ts + 1w] -> [start_ts + 1w, start_ts + 2w] ->...->[start_ts + n*w, end_ts]

        Since we have a clear limit to stop querying what we do is use the startTime/endTime keys
        to filter the data that we need.
        """
        events = []
        if self.is_unified_account is True:
            # unified account can query up to 2 years into the past
            earliest_query_start_ts = Timestamp(ts_now() - DAY_IN_SECONDS * 365 * 2)
        else:
            # classic accounts can query 180 days into the past
            earliest_query_start_ts = Timestamp(ts_now() - DAY_IN_SECONDS * 180)

        if end_ts <= earliest_query_start_ts:
            return []  # entire query out of range

        if start_ts <= earliest_query_start_ts:
            start_ts = Timestamp(earliest_query_start_ts + 60 * 5)  # 5 minutes safety margin
            lower_ts = start_ts

        lower_ts, upper_ts = start_ts, Timestamp(start_ts + WEEK_IN_SECONDS)
        while True:
            # TODO: Use the execution/list endpoint for trades in order to handle fees.
            # See https://github.com/orgs/rotki/projects/11?pane=issue&itemId=104934914
            raw_data = self._paginated_api_query(
                endpoint='order/history',
                options={
                    'category': 'spot',
                    'startTime': str(ts_sec_to_ms(lower_ts)),
                    'endTime': str(ts_sec_to_ms(upper_ts)),
                    'limit': PAGINATION_LIMIT,
                },
            )
            for raw_trade in raw_data:
                if (order_status := raw_trade.get('orderStatus')) != 'Filled':
                    log.debug(f'Skipping entry {raw_trade} with status {order_status}')
                    continue  # api doesn't allow to filter by status in the classic spot

                try:
                    base_asset, quote_asset = bybit_symbol_to_base_quote(
                        symbol=raw_trade['symbol'],
                        four_letter_assets=self.four_letter_assets,
                    )
                except (UnknownAsset, KeyError):
                    log.error(f'Could not read assets from bybit trade {raw_trade}')
                    continue

                try:
                    spend, receive = get_swap_spend_receive(
                        is_buy=deserialize_trade_type_is_buy(raw_trade['side']),
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        amount=deserialize_fval(raw_trade['qty']),
                        rate=deserialize_price(raw_trade['avgPrice' if raw_trade['orderType'] == 'Market' else 'price']),  # noqa: E501
                    )
                    events.extend(create_swap_events(
                        timestamp=TimestampMS(int(raw_trade['updatedTime'])),
                        location=self.location,
                        spend=spend,
                        receive=receive,
                        location_label=self.name,
                        event_identifier=create_event_identifier_from_unique_id(
                            location=self.location,
                            unique_id=raw_trade['orderId'],
                        ),
                    ))
                except DeserializationError as e:
                    log.error(f'{e} when reading rate for bybit trade {raw_trade}')
                except KeyError as e:
                    log.error(
                        f'Failed to deserialize bybit trade {raw_trade} due to missing key {e}. '
                        'Skipping...',
                    )

            lower_ts = Timestamp(lower_ts + WEEK_IN_SECONDS)
            upper_ts = Timestamp(upper_ts + WEEK_IN_SECONDS)
            if lower_ts >= end_ts:
                break

            upper_ts = min(upper_ts, end_ts)  # don't query more than needed in last iteration

        return events

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bybit API key is good for usage in rotki"""
        try:
            self._api_query(path='user/query-api')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def _query_balances_or_error(
            self,
            path: Literal[
                'account/wallet-balance',
                'asset/transfer/query-account-coins-balance',
            ],
            options: dict[str, str],
    ) -> tuple[dict[str, Any], str | None]:
        """Auxiliary function to handle queries of balances to the api.
        Returns a tuple of the response with the balances and a string or None depending
        on whether there was an error.
        """
        try:
            return self._api_query(path=path, options=options), None
        except RemoteError as e:
            msg = f'Bybit request failed. Could not reach the exchange due to {e!s}'
            log.error(msg)
            return {}, msg
        except KeyError as e:
            log.error('Could not query balances for bybit. Check logs for more details')
            return {}, f'Key {e} missing in response'

    def _process_wallet_balances(
            self,
            entries: Sequence[dict[str, Any]],
    ) -> dict[AssetWithOracles, Balance]:
        """Common logic to process balances from the funding and wallet endpoints
        May raise:
        - DeserializationError
        """
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for coin_data in entries:
            try:
                asset = asset_from_bybit(coin_data['coin'])
                if (amount := deserialize_fval(
                    value=coin_data['walletBalance'],
                    name=f'Bybit wallet balance for {asset}',
                    location='bybit',
                )) == ZERO:
                    continue

                if coin_data.get('usdValue', '') != '':
                    usd_value = deserialize_fval(coin_data['usdValue'], name=f'Bybit usd value for {asset}', location='bybit')  # we don't need to calculate it since it is provided by bybit  # noqa: E501
                else:
                    usd_value = Inquirer.find_usd_price(asset=asset) * amount
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                raise DeserializationError(f'Error processing Bybit balance entry {coin_data}. {msg}') from e  # noqa: E501

            assets_balance[asset] += Balance(amount=amount, usd_value=usd_value)

        return assets_balance

    def _query_account_balances(self) -> tuple[dict[AssetWithOracles, Balance], str | None]:
        """
        Query balances in wallet. It queries the unified and spot accounts.
        This call assumes that the first connection has been made to identify the account type.

        Returns the a tuple of balances and None if there wasn't any error or a string
        message with a description of what went wrong.
        """
        asset_balances = {}
        response, error = self._query_balances_or_error(
            path='account/wallet-balance',
            options={'accountType': 'UNIFIED' if self.is_unified_account else 'SPOT'},
        )

        if error is not None:
            return {}, error

        for account in response.get('list', []):
            if (account_coin_data := account.get('coin')) is None:
                log.error(f'There is no information about coins for the bybit account {account}')
                continue

            try:
                asset_balances = self._process_wallet_balances(account_coin_data)
            except DeserializationError as e:
                return {}, str(e)

        return asset_balances, None

    def _query_funding_balances(self) -> tuple[dict[AssetWithOracles, Balance], str | None]:
        """
        Query balances in the funding wallet.
        This call assumes that the first connection has been made to identify the account type.

        Returns the a tuple of balances and None if there wasn't any error or a string
        message with a description of what went wrong.
        """
        asset_balances: dict[AssetWithOracles, Balance] = {}
        response, error = self._query_balances_or_error(
            path='asset/transfer/query-account-coins-balance',
            options={'accountType': 'FUND'},
        )
        if error is not None:
            return {}, error

        try:
            asset_balances = self._process_wallet_balances(response.get('balance', []))
        except DeserializationError as e:
            return {}, str(e)

        return asset_balances, None

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        Query balances at bybit.

        Known limitations:
        - It can't query balance deposited in bots. The API doesn't provide this information
        """
        self.first_connection()

        account_assets_balance, err = self._query_account_balances()
        if err is not None:
            return None, err

        account_funding_balance, err = self._query_funding_balances()
        if err is not None:
            return None, err

        return combine_dicts(a=account_assets_balance, b=account_funding_balance), ''

    def _query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            query_for: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list[AssetMovement]:
        """
        Process deposits/withdrawals from bybit. If any asset is unknown or we fail to
        deserialize an entry the error is logged and we skip the entry.

        This logic doesn't filter by timestamp and instead processes all the entries
        returned by the api discarding those that aren't in start_ts <= timestamp <= end_ts.
        The reason is that the api is poorly designed and you can't know until when to query,
        for any time range the api will return values and is not possible to know when the user
        started to use the api.
        """
        log.debug(f'querying bybit online {query_for} with {start_ts=}-{end_ts=}')
        if query_for == HistoryEventType.DEPOSIT:
            endpoint = 'asset/deposit/query-record'
            timestamp_key = 'successAt'
            fee_key = 'depositFee'
            id_key = 'txID'
        else:
            endpoint = 'asset/withdraw/query-record'
            timestamp_key = 'updateTime'
            fee_key = 'withdrawFee'
            id_key = 'withdrawId'

        raw_data = self._paginated_api_query(
            endpoint=endpoint,  # type: ignore  # mypy doesn't detect that the string is assigned once
            options={'limit': PAGINATION_LIMIT},
        )

        movements = []
        for movement in raw_data:
            if (timestamp_raw := movement.get(timestamp_key)) is not None:
                timestamp = ts_ms_to_sec(TimestampMS(int(timestamp_raw)))
                if not start_ts <= timestamp <= end_ts:
                    continue  # skip if is not in range
            else:
                continue  # skip missing timestamp

            try:
                coin = asset_from_bybit(movement['coin'])
            except UnknownAsset:
                log.error(f'Could not read assets from trade pair {movement["coin"]}')
                continue

            try:
                movements.extend(create_asset_movement_with_fee(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=Location.BYBIT,
                    location_label=self.name,
                    event_type=query_for,
                    asset=coin,
                    amount=deserialize_fval(movement['amount']),
                    fee=AssetAmount(
                        asset=coin,
                        amount=deserialize_fval(movement[fee_key]),
                    ) if len(movement[fee_key]) != 0 else None,
                    unique_id=movement[id_key],
                    extra_data=maybe_set_transaction_extra_data(
                        address=None,
                        transaction_id=movement['txID'],
                    ),
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key {msg}'

                log.error(f'{e} when reading movement for bybit deposit {movement}')
                continue

        return movements

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """Query deposits and withdrawals sequentially"""
        events: list[AssetMovement | SwapEvent] = []
        for event_type in (HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL):
            events.extend(self._query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                query_for=event_type,
            ))

        events.extend(self._query_trades(start_ts=start_ts, end_ts=end_ts))
        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for bybit
