import hashlib
import hmac
import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import BINANCE_BASE_URL, BINANCE_US_BASE_URL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Trade,
    TradeType,
    trade_pair_from_assets,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_binance,
)
from rotkehlchen.typing import ApiKey, ApiSecret, AssetMovementCategory, Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Binance launched at 2017-07-14T04:00:00Z (12:00 GMT+8, Beijing Time)
# https://www.binance.com/en/support/articles/115000599831-Binance-Exchange-Launched-Date-Set
BINANCE_LAUNCH_TS = Timestamp(1500001200)
API_TIME_INTERVAL_CONSTRAINT_TS = Timestamp(7776000)  # 90 days
V3_ENDPOINTS = (
    'account',
    'myTrades',
    'openOrders',
)

V1_ENDPOINTS = (
    'exchangeInfo',
    'time',
    'futures/loan/wallet',
)

WAPI_ENDPOINTS = (
    'depositHistory.html',
    'withdrawHistory.html',
)

SAPI_ENDPOINTS = (
    'futures/loan/wallet',
    'lending/daily/token/position',
    'lending/daily/product/list',
    'lending/union/account',
)

RETRY_AFTER_LIMIT = 60


class BinancePair(NamedTuple):
    """A binance pair. Contains the symbol in the Binance mode e.g. "ETHBTC" and
    the base and quote assets of that symbol as parsed from exchangeinfo endpoint
    result"""
    symbol: str
    binance_base_asset: str
    binance_quote_asset: str


def trade_from_binance(
        binance_trade: Dict,
        binance_symbols_to_pair: Dict[str, BinancePair],
        name: str = 'binance',
) -> Trade:
    """Turn a binance trade returned from trade history to our common trade
    history format

    From the official binance api docs (01/09/18):
    https://github.com/binance-exchange/binance-official-api-docs/blob/62ff32d27bb32d9cc74d63d547c286bb3c9707ef/rest-api.md#terminology

    base asset refers to the asset that is the quantity of a symbol.
    quote asset refers to the asset that is the price of a symbol.

    Throws:
        - UnsupportedAsset due to asset_from_binance
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
    """
    amount = deserialize_asset_amount(binance_trade['qty'])
    rate = deserialize_price(binance_trade['price'])
    if binance_trade['symbol'] not in binance_symbols_to_pair:
        raise DeserializationError(
            f'Error reading a {name} trade. Could not find '
            f'{binance_trade["symbol"]} in binance_symbols_to_pair',
        )

    binance_pair = binance_symbols_to_pair[binance_trade['symbol']]
    timestamp = deserialize_timestamp_from_binance(binance_trade['time'])

    base_asset = asset_from_binance(binance_pair.binance_base_asset)
    quote_asset = asset_from_binance(binance_pair.binance_quote_asset)

    if binance_trade['isBuyer']:
        order_type = TradeType.BUY
        # e.g. in RDNETH we buy RDN by paying ETH
    else:
        order_type = TradeType.SELL

    fee_currency = asset_from_binance(binance_trade['commissionAsset'])
    fee = deserialize_fee(binance_trade['commission'])

    log.debug(
        f'Processing {name} Trade',
        sensitive_log=True,
        amount=amount,
        rate=rate,
        timestamp=timestamp,
        pair=binance_trade['symbol'],
        base_asset=base_asset,
        quote=quote_asset,
        order_type=order_type,
        commision_asset=binance_trade['commissionAsset'],
        fee=fee,
    )

    return Trade(
        timestamp=timestamp,
        location=Location.BINANCE,
        pair=trade_pair_from_assets(base_asset, quote_asset),
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(binance_trade['id']),
    )


def create_binance_symbols_to_pair(exchange_data: Dict[str, Any]) -> Dict[str, BinancePair]:
    """Parses the result of 'exchangeInfo' endpoint and creates the symbols_to_pair mapping
    """
    symbols_to_pair: Dict[str, BinancePair] = {}
    for symbol in exchange_data['symbols']:
        symbol_str = symbol['symbol']
        if isinstance(symbol_str, FVal):
            # the to_int here may rase but should never due to the if check above
            symbol_str = str(symbol_str.to_int(exact=True))

        symbols_to_pair[symbol_str] = BinancePair(
            symbol=symbol_str,
            binance_base_asset=symbol['baseAsset'],
            binance_quote_asset=symbol['quoteAsset'],
        )

    return symbols_to_pair


class Binance(ExchangeInterface):
    """This class supports:
      - Binance: when instantiated with default uri, equals BINANCE_BASE_URL.
      - Binance US: when instantiated with uri equals BINANCE_US_BASE_URL.

    Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/

    Binance US exchange api docs:
    https://github.com/binance-us/binance-official-api-docs

    An unofficial python binance package:
    https://github.com/binance-exchange/python-binance/
    """
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            initial_backoff: int = 4,
            backoff_limit: int = 180,
            uri: str = BINANCE_BASE_URL,
    ):
        exchange_name = str(Location.BINANCE)
        if uri == BINANCE_US_BASE_URL:
            exchange_name = str(Location.BINANCE_US)

        super().__init__(exchange_name, api_key, secret, database)
        self.uri = uri
        self.session.headers.update({
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })
        self.msg_aggregator = msg_aggregator
        self.initial_backoff = initial_backoff
        self.backoff_limit = backoff_limit
        self.nonce_lock = Semaphore()
        self.offset_ms = 0

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        # If it's the first time, populate the binance pair trade symbols
        # We know exchangeInfo returns a dict
        exchange_data = self.api_query_dict('exchangeInfo')
        self._symbols_to_pair = create_binance_symbols_to_pair(exchange_data)

        server_time = self.api_query_dict('time')
        self.offset_ms = server_time['serverTime'] - ts_now_in_ms()

        self.first_connection_made = True

    @property
    def symbols_to_pair(self) -> Dict[str, BinancePair]:
        self.first_connection()
        return self._symbols_to_pair

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            # We know account endpoint returns a dict
            self.api_query_dict('account')
        except RemoteError as e:
            error = str(e)
            if 'API-key format invalid' in error:
                return False, 'Provided API Key is in invalid Format'
            if 'Signature for this request is not valid' in error:
                return False, 'Provided API Secret is malformed'
            if 'Invalid API-key, IP, or permissions for action' in error:
                return False, 'API Key does not match the given secret'
            if 'Timestamp for this request was' in error:
                return False, (
                    f"Local system clock is not in sync with {self.name} server. "
                    f"Try syncing your system's clock"
                )
            # else reraise
            raise

        return True, ''

    def api_query(self, method: str, options: Optional[Dict] = None) -> Union[List, Dict]:
        call_options = options.copy() if options else {}

        while True:
            with self.nonce_lock:
                # Protect this region with a lock since binance will reject
                # non-increasing nonces. So if two greenlets come in here at
                # the same time one of them will fail
                if 'signature' in call_options:
                    del call_options['signature']

                if method in V3_ENDPOINTS or method in WAPI_ENDPOINTS or method in SAPI_ENDPOINTS:
                    if method in SAPI_ENDPOINTS:
                        api_version = 1
                    else:
                        api_version = 3

                    # Recommended recvWindows is 5000 but we get timeouts with it
                    call_options['recvWindow'] = 10000
                    call_options['timestamp'] = str(ts_now_in_ms() + self.offset_ms)
                    signature = hmac.new(
                        self.secret,
                        urlencode(call_options).encode('utf-8'),
                        hashlib.sha256,
                    ).hexdigest()
                    call_options['signature'] = signature
                elif method in V1_ENDPOINTS:
                    api_version = 1
                else:
                    raise ValueError(f'Unexpected {self.name} API method {method}')

                if method in WAPI_ENDPOINTS:
                    apistr = 'wapi/'
                elif method in SAPI_ENDPOINTS:
                    apistr = 'sapi/'
                else:
                    apistr = 'api/'
                request_url = f'{self.uri}{apistr}v{str(api_version)}/{method}?'
                request_url += urlencode(call_options)
                log.debug(f'{self.name} API request', request_url=request_url)
                try:
                    response = self.session.get(request_url)
                except requests.exceptions.RequestException as e:
                    raise RemoteError(
                        f'{self.name} API request failed due to {str(e)}',
                    ) from e

            if response.status_code not in (200, 418, 429):
                code = 'no code found'
                msg = 'no message found'
                try:
                    result = rlk_jsonloads(response.text)
                    if isinstance(result, dict):
                        code = result.get('code', code)
                        msg = result.get('msg', msg)
                except JSONDecodeError:
                    pass

                raise RemoteError(
                    '{} API request {} for {} failed with HTTP status '
                    'code: {}, error code: {} and error message: {}'.format(
                        self.name,
                        response.url,
                        method,
                        response.status_code,
                        code,
                        msg,
                    ))

            if response.status_code in (418, 429):
                # Binance has limits and if we hit them we should backoff.
                # A Retry-After header is sent with a 418 or 429 responses and
                # will give the number of seconds required to wait, in the case
                # of a 429, to prevent a ban, or, in the case of a 418, until
                # the ban is over.
                # https://binance-docs.github.io/apidocs/spot/en/#limits
                retry_after = int(response.headers.get('retry-after', '0'))
                log.debug(
                    f'Got status code {response.status_code} from {self.name}. Backing off',
                    seconds=retry_after,
                )
                if retry_after > RETRY_AFTER_LIMIT:
                    raise RemoteError(
                        '{} API request {} for {} failed with HTTP status '
                        'code: {} due to a too long retry after value (> {})'.format(
                            self.name,
                            response.url,
                            method,
                            response.status_code,
                            RETRY_AFTER_LIMIT,
                        ))

                gevent.sleep(retry_after)
                continue

            # else success
            break

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
            ) from e
        return json_ret

    def api_query_dict(self, method: str, options: Optional[Dict] = None) -> Dict:
        result = self.api_query(method, options)
        assert isinstance(result, Dict)  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
        return result

    def api_query_list(self, method: str, options: Optional[Dict] = None) -> List:
        result = self.api_query(method, options)
        assert isinstance(result, List)  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
        return result

    def _query_spot_balances(self, balances: Dict) -> Dict:
        account_data = self.api_query_dict('account')
        for entry in account_data['balances']:
            if len(entry['asset']) >= 5 and entry['asset'].startswith('LD'):
                # Some lending coins also appear to start with the LD prefix. Ignore them
                continue

            amount = entry['free'] + entry['locked']
            if amount == ZERO:
                continue

            try:
                asset = asset_from_binance(entry['asset'])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported {self.name} asset {e.asset_name}. '
                    f'Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown {self.name} asset {e.asset_name}. '
                    f'Ignoring its balance query.',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Found {self.name} asset with non-string type {type(entry["asset"])}. '
                    f'Ignoring its balance query.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balance = {}
            balance['amount'] = amount
            balance['usd_value'] = FVal(amount * usd_price)

            if asset not in balances:
                balances[asset] = balance
            else:  # Some assets may appear twice in binance balance query for different locations
                # Lending/staking for example
                balances[asset]['amount'] += balance['amount']
                balances[asset]['usd_value'] += balance['usd_value']

        return balances

    def _query_lending_balances(self, balances: Dict) -> Dict:
        data = self.api_query_dict('lending/union/account')
        positions = data.get('positionAmountVos', None)
        if positions is None:
            raise RemoteError(
                f'Could not find key positionAmountVos in lending account data '
                f'{data} returned by {self.name}.',
            )

        for entry in positions:
            try:
                amount = FVal(entry['amount'])
                if amount == ZERO:
                    continue

                asset = asset_from_binance(entry['asset'])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported {self.name} asset {e.asset_name}. '
                    f'Ignoring its lending balance query.',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown {self.name} asset {e.asset_name}. '
                    f'Ignoring its lending balance query.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error at deserializing {self.name} asset. {msg}. '
                    f'Ignoring its lending balance query.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balance = Balance(amount=amount, usd_value=amount * usd_price)
            if asset not in balances:
                balances[asset] = balance.to_dict()
            else:
                balances[asset]['amount'] += balance.amount
                balances[asset]['usd_value'] += balance.usd_value

        return balances

    def _query_futures_balances(self, balances: Dict) -> Dict:
        futures_response = self.api_query_dict('futures/loan/wallet')
        try:
            cross_collaterals = futures_response['crossCollaterals']
            for entry in cross_collaterals:
                amount = FVal(entry['locked'])
                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_binance(entry['collateralCoin'])
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported {self.name} asset {e.asset_name}. '
                        f'Ignoring its futures balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown {self.name} asset {e.asset_name}. '
                        f'Ignoring its futures balance query.',
                    )
                    continue
                except DeserializationError:
                    self.msg_aggregator.add_error(
                        f'Found {self.name} asset with non-string type '
                        f'{type(entry["asset"])}. Ignoring its futures balance query.',
                    )
                    continue

                try:
                    usd_price = Inquirer().find_usd_price(asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                balance = Balance(amount=amount, usd_value=amount * usd_price)
                if asset not in balances:
                    balances[asset] = balance.to_dict()
                else:
                    balances[asset]['amount'] += balance.amount
                    balances[asset]['usd_value'] += balance.usd_value

        except KeyError as e:
            self.msg_aggregator.add_error(
                f'At {self.name} futures balance query did not find expected key '
                f'{str(e)}. Skipping futures query...',
            )

        return balances

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[Dict], str]:
        self.first_connection()
        returned_balances: Dict = {}
        try:
            returned_balances = self._query_spot_balances(returned_balances)
            returned_balances = self._query_futures_balances(returned_balances)
            returned_balances = self._query_lending_balances(returned_balances)
        except RemoteError as e:
            msg = (
                f'{self.name} account API request failed. '
                f'Could not reach binance due to {str(e)}'
            )
            self.msg_aggregator.add_error(msg)
            return None, msg

        log.debug(
            f'{self.name} balance query result',
            sensitive_log=True,
            balances=returned_balances,
        )
        return returned_balances, ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            markets: Optional[List[str]] = None,
    ) -> List[Trade]:
        self.first_connection()

        if not markets:
            iter_markets = list(self._symbols_to_pair.keys())
        else:
            iter_markets = markets

        raw_data = []
        # Limit of results to return. 1000 is max limit according to docs
        limit = 1000
        for symbol in iter_markets:
            last_trade_id = 0
            len_result = limit
            while len_result == limit:
                # We know that myTrades returns a list from the api docs
                result = self.api_query_list(
                    'myTrades',
                    options={
                        'symbol': symbol,
                        'fromId': last_trade_id,
                        'limit': limit,
                        # Not specifying them since binance does not seem to
                        # respect them and always return all trades
                        # 'startTime': start_ts * 1000,
                        # 'endTime': end_ts * 1000,
                    })
                if result:
                    last_trade_id = result[-1]['id'] + 1
                len_result = len(result)
                log.debug(f'{self.name} myTrades query result', results_num=len_result)
                for r in result:
                    r['symbol'] = symbol
                raw_data.extend(result)

            raw_data.sort(key=lambda x: x['time'])

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_binance(
                    binance_trade=raw_trade,
                    binance_symbols_to_pair=self.symbols_to_pair,
                    name=self.name,
                )
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} trade with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error processing a {self.name} trade. Check logs '
                    f'for details. Ignoring it.',
                )
                log.error(
                    f'Error processing a {self.name} trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue

            # Since binance does not respect the given timestamp range, limit the range here
            if trade.timestamp < start_ts:
                continue

            if trade.timestamp > end_ts:
                break

            trades.append(trade)

        return trades

    def _deserialize_asset_movement(self, raw_data: Dict[str, Any]) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if 'insertTime' in raw_data:
                category = AssetMovementCategory.DEPOSIT
                time_key = 'insertTime'
            else:
                category = AssetMovementCategory.WITHDRAWAL
                time_key = 'applyTime'

            timestamp = deserialize_timestamp_from_binance(raw_data[time_key])
            asset = asset_from_binance(raw_data['asset'])
            return AssetMovement(
                location=Location.BINANCE,
                category=category,
                address=deserialize_asset_movement_address(raw_data, 'address', asset),
                transaction_id=get_key_if_has_val(raw_data, 'txId'),
                timestamp=timestamp,
                asset=asset,
                amount=deserialize_asset_amount_force_positive(raw_data['amount']),
                fee_asset=asset,
                # Binance does not include withdrawal fees neither in the API nor in their UI
                fee=Fee(ZERO),
                link=str(raw_data['txId']),
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {self.name} deposit/withdrawal. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {self.name} deposit_withdrawal',
                asset_movement=raw_data,
                error=msg,
            )

        return None

    def _api_query_dict_within_time_delta(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            time_delta: Timestamp,
            method: Literal['depositHistory.html', 'withdrawHistory.html'],
    ) -> List[Dict[str, Any]]:
        """Request via `api_query_dict()` from `start_ts` `end_ts` using a time
        delta (offset) less than `time_delta`.

        Be aware of:
          - If `start_ts` equals zero, the Binance launch timestamp is used
          (from BINANCE_LAUNCH_TS). This value is not stored in the
          `used_query_ranges` table, but 0.
          - Timestamps are converted to milliseconds.
        """
        if method == 'depositHistory.html':
            query_schema = 'depositList'
        elif method == 'withdrawHistory.html':
            query_schema = 'withdrawList'
        else:
            raise AssertionError(f'Unexpected {self.name} method case: {method}.')

        results: List[Dict[str, Any]] = []

        # Create required time references in milliseconds
        start_ts = Timestamp(start_ts * 1000)
        end_ts = Timestamp(end_ts * 1000)
        offset = time_delta * 1000 - 1  # less than time_delta
        if start_ts == Timestamp(0):
            from_ts = BINANCE_LAUNCH_TS * 1000
        else:
            from_ts = start_ts

        to_ts = (
            from_ts + offset  # Case request with offset
            if end_ts - from_ts > offset
            else end_ts  # Case request without offset (1 request)
        )
        while True:
            options = {
                'timestamp': ts_now_in_ms(),
                'startTime': from_ts,
                'endTime': to_ts,
            }
            result = self.api_query_dict(method, options=options)
            results.extend(result.get(query_schema, []))
            # Case stop requesting
            if to_ts >= end_ts:
                break

            from_ts = to_ts + 1
            to_ts = min(to_ts + offset, end_ts)

        return results

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """
        Be aware of:
          - Timestamps must be in milliseconds.
          - There must be less than 90 days between start and end timestamps.

        Deposit & Withdraw history documentation:
        https://binance-docs.github.io/apidocs/spot/en/#deposit-history-user_data
        https://binance-docs.github.io/apidocs/spot/en/#withdraw-history-user_data
        """
        deposits = self._api_query_dict_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            method='depositHistory.html',
        )
        log.debug(f'{self.name} deposit history result', results_num=len(deposits))

        withdraws = self._api_query_dict_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            method='withdrawHistory.html',
        )
        log.debug(f'{self.name} withdraw history result', results_num=len(withdraws))

        movements = []
        for raw_movement in deposits + withdraws:
            movement = self._deserialize_asset_movement(raw_movement)
            if movement:
                movements.append(movement)

        return movements
