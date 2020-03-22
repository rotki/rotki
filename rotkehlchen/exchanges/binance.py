import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, NamedTuple, Optional, Tuple, Union
from urllib.parse import urlencode

import gevent
from gevent.lock import Semaphore

from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import BINANCE_BASE_URL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Trade,
    TradeType,
    trade_pair_from_assets,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_binance,
)
from rotkehlchen.typing import ApiKey, ApiSecret, AssetMovementCategory, Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import ts_now, ts_now_in_ms
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

V3_ENDPOINTS = (
    'account',
    'myTrades',
    'openOrders',
)

V1_ENDPOINTS = (
    'exchangeInfo'
)

WAPI_ENDPOINTS = (
    'depositHistory.html',
    'withdrawHistory.html',
)


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
            f'Error reading a binance trade. Could not find '
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
        'Processing binance Trade',
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
    """Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/

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
    ):
        super(Binance, self).__init__('binance', api_key, secret, database)
        self.uri = BINANCE_BASE_URL
        self.session.headers.update({
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })
        self.msg_aggregator = msg_aggregator
        self.initial_backoff = initial_backoff
        self.backoff_limit = backoff_limit
        self.nonce_lock = Semaphore()

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        # If it's the first time, populate the binance pair trade symbols
        # We know exchangeInfo returns a dict
        exchange_data = self.api_query_dict('exchangeInfo')
        self._symbols_to_pair = create_binance_symbols_to_pair(exchange_data)

        self.first_connection_made = True

    @property
    def symbols_to_pair(self) -> Dict[str, BinancePair]:
        self.first_connection()
        return self._symbols_to_pair

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            # We know account endpoint returns a dict
            self.api_query_dict('account')
        except ValueError as e:
            error = str(e)
            if 'API-key format invalid' in error:
                return False, 'Provided API Key is in invalid Format'
            elif 'Signature for this request is not valid' in error:
                return False, 'Provided API Secret is malformed'
            elif 'Invalid API-key, IP, or permissions for action' in error:
                return False, 'API Key does not match the given secret'
            else:
                raise
        return True, ''

    def api_query(self, method: str, options: Optional[Dict] = None) -> Union[List, Dict]:
        if not options:
            options = {}

        backoff = self.initial_backoff

        while True:
            with self.nonce_lock:
                # Protect this region with a lock since binance will reject
                # non-increasing nonces. So if two greenlets come in here at
                # the same time one of them will fail
                if method in V3_ENDPOINTS or method in WAPI_ENDPOINTS:
                    api_version = 3
                    # Recommended recvWindows is 5000 but we get timeouts with it
                    options['recvWindow'] = 10000
                    options['timestamp'] = str(ts_now_in_ms())
                    signature = hmac.new(
                        self.secret,
                        urlencode(options).encode('utf-8'),
                        hashlib.sha256,
                    ).hexdigest()
                    options['signature'] = signature
                elif method in V1_ENDPOINTS:
                    api_version = 1
                else:
                    raise ValueError('Unexpected binance api method {}'.format(method))

                apistr = 'wapi/' if method in WAPI_ENDPOINTS else 'api/'
                request_url = f'{self.uri}{apistr}v{str(api_version)}/{method}?'
                request_url += urlencode(options)

                log.debug('Binance API request', request_url=request_url)

                response = self.session.get(request_url)

            limit_ban = response.status_code == 429 and backoff > self.backoff_limit
            if limit_ban or response.status_code not in (200, 429):
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
                    'Binance API request {} for {} failed with HTTP status '
                    'code: {}, error code: {} and error message: {}'.format(
                        response.url,
                        method,
                        response.status_code,
                        code,
                        msg,
                    ))
            elif response.status_code == 429:
                if backoff > self.backoff_limit:
                    break
                # Binance has limits and if we hit them we should backoff
                # https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#limits
                log.debug('Got 429 from Binance. Backing off', seconds=backoff)
                gevent.sleep(backoff)
                backoff = backoff * 2
                continue
            else:
                # success
                break

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError:
            raise RemoteError(f'Binance returned invalid JSON response: {response.text}')
        return json_ret

    def api_query_dict(self, method: str, options: Optional[Dict] = None) -> Dict:
        result = self.api_query(method, options)
        assert isinstance(result, Dict)
        return result

    def api_query_list(self, method: str, options: Optional[Dict] = None) -> List:
        result = self.api_query(method, options)
        assert isinstance(result, List)
        return result

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:
        self.first_connection()

        try:
            # account data returns a dict as per binance docs
            account_data = self.api_query_dict('account')
        except RemoteError as e:
            msg = (
                'Binance API request failed. Could not reach binance due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances = {}
        for entry in account_data['balances']:
            amount = entry['free'] + entry['locked']
            if amount == FVal(0):
                continue
            try:
                asset = asset_from_binance(entry['asset'])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported binance asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown binance asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Found binance asset with non-string type {type(entry["asset"])}. '
                    f' Ignoring its balance query.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing binance balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balance = {}
            balance['amount'] = amount
            balance['usd_value'] = FVal(amount * usd_price)
            returned_balances[asset] = balance

            log.debug(
                'binance balance query result',
                sensitive_log=True,
                asset=asset,
                amount=amount,
                usd_value=balance['usd_value'],
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
                log.debug('binance myTrades query result', results_num=len_result)
                for r in result:
                    r['symbol'] = symbol
                raw_data.extend(result)

            raw_data.sort(key=lambda x: x['time'])

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_binance(raw_trade, self.symbols_to_pair)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found binance trade with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found binance trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a binance trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a binance trade',
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
            amount = deserialize_asset_amount(raw_data['amount'])
            return AssetMovement(
                location=Location.BINANCE,
                category=category,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                # Binance does not include withdrawal fees neither in the API nor in their UI
                fee=Fee(ZERO),
                link=str(raw_data['txId']),
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found binance deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found binance deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Error processing a binance deposit/withdrawal. Check logs '
                'for details. Ignoring it.',
            )
            log.error(
                'Error processing a binance deposit_withdrawal',
                asset_movement=raw_data,
                error=msg,
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        # This does not check for any limits. Can there be any limits like with trades
        # in the deposit/withdrawal binance api? Can't see anything in the docs:
        # https://github.com/binance-exchange/binance-official-api-docs/blob/master/wapi-api.md#deposit-history-user_data
        #
        # Note that all timestamps should be in milliseconds, so we multiply by 1k
        options = {
            'timestamp': ts_now_in_ms(),
            'startTime': start_ts * 1000,
            'endTime': end_ts * 1000,
        }
        result = self.api_query_dict('depositHistory.html', options=options)
        raw_data = result.get('depositList', [])
        options['timestamp'] = ts_now_in_ms()
        result = self.api_query_dict('withdrawHistory.html', options=options)
        raw_data.extend(result.get('withdrawList', []))
        log.debug('binance deposit/withdrawal history result', results_num=len(raw_data))

        movements = []
        for raw_movement in raw_data:
            movement = self._deserialize_asset_movement(raw_movement)
            if movement:
                movements.append(movement)

        return movements
