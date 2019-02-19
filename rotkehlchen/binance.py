import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union, cast
from urllib.parse import urlencode

import gevent

from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchange import Exchange
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ApiKey, ApiSecret, FilePath, Timestamp, Trade
from rotkehlchen.utils import cache_response_timewise, rlk_jsonloads

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


class BinancePair(NamedTuple):
    symbol: str
    base_asset: str
    quote_asset: str


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
    """
    amount = FVal(binance_trade['qty'])
    rate = FVal(binance_trade['price'])
    pair = binance_symbols_to_pair[binance_trade['symbol']]
    timestamp = binance_trade['time']

    base_asset = pair.base_asset
    quote_asset = pair.quote_asset

    if binance_trade['isBuyer']:
        order_type = 'buy'
        # e.g. in RDNETH we buy RDN by paying ETH
    else:
        order_type = 'sell'

    fee_currency = binance_trade['commissionAsset']
    fee = FVal(binance_trade['commission'])

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
        location='binance',
        pair=base_asset + '_' + quote_asset,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
    )


class Binance(Exchange):
    """Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md

    An unofficial python binance package:
    https://github.com/sammchardy/python-binance
    """
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            inquirer: Inquirer,
            data_dir: FilePath,
            initial_backoff: int = 4,
            backoff_limit: int = 180,
    ):
        super(Binance, self).__init__('binance', api_key, secret, data_dir)
        self.apiversion = 'v3'
        self.uri = 'https://api.binance.com/api/'
        self.inquirer = inquirer
        self.session.headers.update({  # type: ignore
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })
        self.initial_backoff = initial_backoff
        self.backoff_limit = backoff_limit

    def first_connection(self):
        if self.first_connection_made:
            return

        # If it's the first time, populate the binance pair trade symbols
        # We know exchangeInfo returns a dict
        exchange_data = self.api_query('exchangeInfo')
        self._populate_symbols_to_pair(exchange_data)

        self.first_connection_made = True

    def _populate_symbols_to_pair(self, exchange_data: Dict[str, Any]):
        self._symbols_to_pair: Dict[str, BinancePair] = dict()
        for symbol in exchange_data['symbols']:
            symbol_str = symbol['symbol']
            if isinstance(symbol_str, FVal):
                symbol_str = str(symbol_str.to_int(exact=True))

            self._symbols_to_pair[symbol_str] = BinancePair(
                symbol=symbol_str,
                base_asset=symbol['baseAsset'],
                quote_asset=symbol['quoteAsset'],
            )

    @property
    def symbols_to_pair(self) -> Dict[str, BinancePair]:
        self.first_connection()
        return self._symbols_to_pair

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            # We know account endpoint returns a dict
            self.api_query('account')
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
            with self.lock:
                # Protect this region with a lock since binance will reject
                # non-increasing nonces. So if two greenlets come in here at
                # the same time one of them will fail
                if method in V3_ENDPOINTS:
                    api_version = 3
                    # Recommended recvWindows is 5000 but we get timeouts with it
                    options['recvWindow'] = 10000
                    options['timestamp'] = str(int(time.time() * 1000))
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

                request_url = self.uri + 'v' + str(api_version) + '/' + method + '?'
                request_url += urlencode(options)

                log.debug('Binance API request', request_url=request_url)

                response = self.session.get(request_url)

            limit_ban = response.status_code == 429 and backoff > self.backoff_limit
            if limit_ban or response.status_code not in (200, 429):
                result = rlk_jsonloads(response.text)
                code = 'no code found'
                msg = 'no message found'
                if isinstance(result, dict):
                    code = result['code']
                    msg = result['msg']
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

        json_ret = rlk_jsonloads(response.text)
        return json_ret

    @cache_response_timewise(CACHE_RESPONSE_FOR_SECS)
    def query_balances(self) -> Tuple[Optional[dict], str]:
        self.first_connection()

        try:
            # account data returns a dict as per binance docs
            account_data = cast(Dict, self.api_query('account'))
        except RemoteError as e:
            msg = (
                'Binance API request failed. Could not reach binance due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances = dict()
        for entry in account_data['balances']:
            amount = entry['free'] + entry['locked']
            if amount == FVal(0):
                continue
            currency = entry['asset']
            usd_price = self.inquirer.find_usd_price(currency)
            balance = dict()
            balance['amount'] = amount
            balance['usd_value'] = FVal(amount * usd_price)
            returned_balances[currency] = balance

            log.debug(
                'binance balance query result',
                sensitive_log=True,
                currency=currency,
                amount=amount,
                usd_value=balance['usd_value'],
            )

        return returned_balances, ''

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
            markets: Optional[str] = None,
    ) -> List:
        cache = self.check_trades_cache(start_ts, end_at_least_ts)
        cache = cast(List, cache)
        if cache is not None:
            return cache

        self.first_connection()

        if not markets:
            markets = self._symbols_to_pair.keys()

        all_trades_history = list()
        # Limit of results to return. 1000 is max limit according to docs
        limit = 1000
        for symbol in markets:
            last_trade_id = 0
            len_result = limit
            while len_result == limit:
                # We know that myTrades returns a list from the api docs
                result = self.api_query(
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
                all_trades_history.extend(result)

        all_trades_history.sort(key=lambda x: x['time'])

        returned_history = list()
        for order in all_trades_history:
            order_timestamp = int(order['time'] / 1000)
            if start_ts is not None and order_timestamp < start_ts:
                continue
            if end_ts is not None and order_timestamp > end_ts:
                break
            order['time'] = order_timestamp

            returned_history.append(order)

        self.update_trades_cache(returned_history, start_ts, end_ts)
        return returned_history
