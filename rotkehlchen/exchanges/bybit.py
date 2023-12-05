import hashlib
import hmac
import json
import logging
import urllib.parse
from collections import defaultdict
from http import HTTPStatus
from multiprocessing.managers import RemoteError
from typing import TYPE_CHECKING, Any, Final, Literal

import gevent
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bybit
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import pair_symbol_to_base_quote
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_fval,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    ExchangeAuthCredentials,
    Fee,
    Location,
    Timestamp,
    TimestampMS,
    TradeType,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_now_in_ms, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryEvent
    from rotkehlchen.user_messages import MessagesAggregator


PAGINATION_LIMIT: Final = 50
# RECEIV_WINDOW specifies how long an HTTP request is valid.
# It is also used to prevent replay attacks. its unit in ms
# https://bybit-exchange.github.io/docs/v5/guide#parameters-for-authenticated-endpoints
RECEIV_WINDOW: Final = '5000'
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def bybit_symbol_to_base_quote(symbol: str) -> tuple[AssetWithOracles, AssetWithOracles]:
    """Turns a bybit symbol product into a base/quote asset tuple

    - Can raise UnprocessableTradePair if symbol is in unexpected format
    - Can raise UnknownAsset if any of the pair assets are not known to rotki
    """
    five_letter_assets = ('SUSHI', '1INCH', 'MATIC', 'TENET', 'LOOKS', 'SFUND')
    six_letter_assets = ('KARATE', 'PSTAKE', 'PRIMAL', 'PLANET', 'PENDLE', 'PEOPLE', 'TURBOS')
    # bybit has special pairs with perpetuals/shorts of the tokens
    split_symbol = None
    if '2L' in symbol:
        split_symbol = symbol.split('2L')
    elif '2S' in symbol:
        split_symbol = symbol.split('2S')
    elif '2' in symbol:
        split_symbol = symbol.split('2')

    if split_symbol is not None and len(split_symbol) == 2:
        base_asset = asset_from_bybit(split_symbol[0])
        quote_asset = asset_from_bybit(split_symbol[1])
    else:
        base_asset, quote_asset = pair_symbol_to_base_quote(
            symbol=symbol,
            asset_deserialize_fn=asset_from_bybit,
            five_letter_assets=five_letter_assets,
            six_letter_assets=six_letter_assets,
        )

    return base_asset, quote_asset


class Bybit(ExchangeInterface):
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
        )
        self.uri = 'https://api.bybit.com/v5'
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-RECV-WINDOW': RECEIV_WINDOW,
            'X-BAPI-API-KEY': self.api_key,
        })
        self.authenticated_methods = {
            'account/wallet-balance',
            'account/transaction-log',
            'order/history',
            'user/query-api',
            'asset/deposit/query-record',
            'asset/withdraw/query-record',
        }
        self.is_unified_account = False
        self.history_events_db = DBHistoryEvents(self.db)

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

        while True:
            log.debug('Bybit API Query', url=url, options=options)
            if requires_auth:
                timestamp = ts_now_in_ms()
                # the order in this string is defined by the api
                param_str = str(timestamp) + self.api_key + RECEIV_WINDOW
                if options is not None:
                    options = dict(sorted(options.items()))
                    param_str += '&'.join(  # params need to be sorted to be correctly validated
                        [
                            str(k) + '=' + urllib.parse.quote_plus(str(v))  # need to use the quoted string since cursors have `=` and it breaks signatures  # noqa: E501
                            for k, v in sorted(options.items())
                            if v is not None
                        ],
                    )

                signature_hash = hmac.new(
                    key=self.secret,
                    msg=param_str.encode('utf-8'),
                    digestmod=hashlib.sha256,
                )
                signature = signature_hash.hexdigest()
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
                    headers=headers if requires_auth is True else None,
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

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
        """
        Query trades from bybit in the spot category.
        The API is limited to query trades up to two years into the past. We can query time ranges
        but we don't know when to stop querying into the past. What this function does is iterate
        over the 2 years period moving the queried frame in the maximum allowed time span, that is
        one week:
        [end ts, end ts - 1 week] -> [end ts - 1w, end ts - 2w] -> ... [end ts - n*w, start ts]

        Since we have a clear limit to stop querying what we do is use the startTime/endTime keys
        to filter the data that we need.
        """
        new_trades = []
        upper_ts, lower_ts = end_ts, Timestamp(end_ts - WEEK_IN_SECONDS)
        two_years_ago = Timestamp(ts_now() - DAY_IN_SECONDS * 365 * 2)
        if start_ts < two_years_ago:
            # bybit allows to query up to two years into the past
            start_ts = two_years_ago

        while True:
            raw_data = self._paginated_api_query(
                endpoint='order/history',
                options={
                    'category': 'spot',
                    'endTime': str(ts_sec_to_ms(upper_ts)),
                    'limit': PAGINATION_LIMIT,
                    'startTime': str(ts_sec_to_ms(lower_ts)),
                },
            )
            for raw_trade in raw_data:
                if (order_status := raw_trade.get('orderStatus')) != 'Filled':
                    log.debug(f'Skipping entry {raw_trade} with status {order_status}')
                    continue  # api doesn't allow to filter by status in the classic spot

                try:
                    base_asset, quote_asset = bybit_symbol_to_base_quote(raw_trade['symbol'])
                except (UnknownAsset, UnprocessableTradePair, KeyError):
                    log.error(f'Could not read assets from bybit trade {raw_trade}')
                    continue

                try:
                    if raw_trade['orderType'] == 'Market':
                        rate = deserialize_price(raw_trade['avgPrice'])
                    else:
                        rate = deserialize_price(raw_trade['price'])

                    trade = Trade(
                        timestamp=ts_ms_to_sec(TimestampMS(int(raw_trade['updatedTime']))),
                        location=Location.BYBIT,
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        trade_type=TradeType.deserialize(raw_trade['side']),
                        amount=deserialize_asset_amount(raw_trade['qty']),
                        rate=rate,
                        fee=deserialize_fee(raw_trade['cumExecFee']) if len(raw_trade['cumExecFee']) else Fee(ZERO),  # noqa: E501
                        link=raw_trade['orderLinkId'],
                    )
                except DeserializationError as e:
                    log.error(f'{e} when reading rate for bybit trade {raw_trade}')
                except KeyError as e:
                    log.error(
                        f'Failed to deserialize bybit trade {raw_trade} due to missing key {e}. '
                        'Skipping...',
                    )
                else:
                    new_trades.append(trade)

            upper_ts = Timestamp(upper_ts - WEEK_IN_SECONDS)
            lower_ts = Timestamp(lower_ts - WEEK_IN_SECONDS)
            if upper_ts <= start_ts:
                break

            if lower_ts < start_ts:  # don't query more than what we need in last iteration
                lower_ts = start_ts

        return new_trades, (start_ts, end_ts)

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bybit API key is good for usage in rotki"""
        try:
            self._api_query(path='user/query-api')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        Query balances at bybit.

        Known limitations:
        - It can't query balance deposited in bots. The API doesn't provide this information
        """
        self.first_connection()
        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)

        try:
            response = self._api_query(
                path='account/wallet-balance',
                options={
                    'accountType': 'UNIFIED' if self.is_unified_account else 'SPOT',
                },
            )['list']
        except RemoteError as e:
            msg = f'Bybit request failed. Could not reach the exchange due to {e!s}'
            log.error(msg)
            return None, msg
        except KeyError as e:
            log.error('Could not query balances for bybit. Check logs for more details')
            return None, f'Key {e} missing in response'

        for account in response:
            if (account_coin_data := account.get('coin')) is None:
                log.error(f'There is no information about coins for the bybit account {account}')
                continue

            for coin_data in account_coin_data:
                try:
                    asset = asset_from_bybit(coin_data['coin'])
                    amount = deserialize_fval(coin_data['walletBalance'], name=f'Bybit wallet balance for {asset}', location='bybit')  # noqa: E501
                    if coin_data['usdValue'] != '':
                        usd_value = deserialize_fval(coin_data['usdValue'], name=f'Bybit usd value for {asset}', location='bybit')  # we don't need to calculate it since it is provided by bybit  # noqa: E501
                    else:
                        usd_price = Inquirer().find_usd_price(asset=asset)
                        usd_value = usd_price * amount
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

    def _query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            query_for: AssetMovementCategory,
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
        if query_for == AssetMovementCategory.DEPOSIT:
            endpoint = 'asset/deposit/query-record'
            timestamp_key = 'successAt'
            fee_key = 'depositFee'
            link_key = 'txID'
        else:
            endpoint = 'asset/withdraw/query-record'
            timestamp_key = 'updateTime'
            fee_key = 'withdrawFee'
            link_key = 'withdrawId'

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
                movements.append(AssetMovement(
                    timestamp=timestamp,
                    location=Location.BYBIT,
                    category=query_for,
                    address=None,
                    transaction_id=movement['txID'],
                    asset=coin,
                    amount=deserialize_asset_amount(movement['amount']),
                    fee_asset=coin,
                    fee=deserialize_fee(movement[fee_key]) if len(movement[fee_key]) else Fee(ZERO),  # noqa: E501,
                    link=movement[link_key],
                ))
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key {msg}'

                log.error(f'{e} when reading movement for bybit deposit {movement}')
                continue

        return movements

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals sequentially"""
        new_movements = self._query_deposits_withdrawals(
            start_ts=start_ts,
            end_ts=end_ts,
            query_for=AssetMovementCategory.DEPOSIT,
        )
        new_movements.extend(
            self._query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                query_for=AssetMovementCategory.WITHDRAWAL,
            ),
        )
        return new_movements

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
