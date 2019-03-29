import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_bittrex
from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.errors import RemoteError, UnsupportedAsset
from rotkehlchen.exchange import Exchange
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.order_formatting import (
    Trade,
    TradeType,
    get_pair_position_asset,
    get_pair_position_str,
    pair_get_assets,
)
from rotkehlchen.typing import ApiKey, ApiSecret, FilePath, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils import cache_response_timewise, createTimeStamp, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


BITTREX_MARKET_METHODS = {
    'getopenorders',
    'cancel',
    'sellmarket',
    'selllimit',
    'buymarket',
    'buylimit',
}
BITTREX_ACCOUNT_METHODS = {
    'getbalances',
    'getbalance',
    'getdepositaddress',
    'withdraw',
    'getorderhistory',
}


def bittrex_pair_to_world(given_pair: str) -> TradePair:
    """
    Turns a pair written in the bittrex way to Rotkehlchen way

    Throws:
        - UnsupportedAsset due to asset_from_bittrex()
    """
    pair = TradePair(given_pair.replace('-', '_'))
    base_currency = asset_from_bittrex(get_pair_position_str(pair, 'first'))
    quote_currency = asset_from_bittrex(get_pair_position_str(pair, 'second'))

    # Since in Bittrex the base currency is the cost currency, iow in Bittrex
    # for BTC_ETH we buy ETH with BTC and sell ETH for BTC, we need to turn it
    # into the Rotkehlchen way which is following the base/quote approach.
    pair = TradePair(f'{quote_currency}_{base_currency}')
    return pair


def world_pair_to_bittrex(pair: TradePair) -> str:
    """Turns a rotkehlchen pair to a bittrex pair"""
    base_asset, quote_asset = pair_get_assets(pair)

    base_asset_str = base_asset.to_bittrex()
    quote_asset_str = quote_asset.to_bittrex()

    # In bittrex the pairs are inverted and use '-'
    return f'{quote_asset_str}-{base_asset_str}'


def trade_from_bittrex(bittrex_trade: Dict[str, Any]) -> Trade:
    """Turn a bittrex trade returned from bittrex trade history to our common trade
    history format

    Throws:
        - UnsupportedAsset due to bittrex_pair_to_world()
"""
    amount = FVal(bittrex_trade['Quantity']) - FVal(bittrex_trade['QuantityRemaining'])
    rate = FVal(bittrex_trade['PricePerUnit'])
    order_type = bittrex_trade['OrderType']
    bittrex_price = FVal(bittrex_trade['Price'])
    bittrex_commission = FVal(bittrex_trade['Commission'])
    pair = bittrex_pair_to_world(bittrex_trade['Exchange'])
    quote_currency = get_pair_position_asset(pair, 'second')
    fee = bittrex_commission
    if order_type == 'LIMIT_BUY':
        order_type = TradeType.BUY
    elif order_type == 'LIMIT_SEL':
        order_type = TradeType.SELL
    else:
        raise ValueError('Got unexpected order type "{}" for bittrex trade'.format(order_type))

    log.debug(
        'Processing bittrex Trade',
        sensitive_log=True,
        amount=amount,
        rate=rate,
        order_type=order_type,
        price=bittrex_price,
        fee=bittrex_commission,
        bittrex_pair=bittrex_trade['Exchange'],
        pair=pair,
    )

    return Trade(
        timestamp=bittrex_trade['TimeStamp'],
        location='bittrex',
        pair=pair,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=quote_currency,
    )


class Bittrex(Exchange):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            inquirer: Inquirer,
            user_directory: FilePath,
            msg_aggregator: MessagesAggregator,
    ):
        super(Bittrex, self).__init__('bittrex', api_key, secret, user_directory)
        self.apiversion = 'v1.1'
        self.uri = 'https://bittrex.com/api/{}/'.format(self.apiversion)
        self.inquirer = inquirer
        self.msg_aggregator = msg_aggregator

    def first_connection(self):
        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self.api_query('getbalance', {'currency': 'BTC'})
        except ValueError as e:
            error = str(e)
            if error == 'APIKEY_INVALID':
                return False, 'Provided API Key is invalid'
            elif error == 'INVALID_SIGNATURE':
                return False, 'Provided API Secret is invalid'
            else:
                raise
        return True, ''

    def api_query(
            self,
            method: str,
            options: Optional[Dict] = None,
    ) -> Union[List, Dict]:
        """
        Queries Bittrex with given method and options
        """
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))
        method_type = 'public'

        if method in BITTREX_MARKET_METHODS:
            method_type = 'market'
        elif method in BITTREX_ACCOUNT_METHODS:
            method_type = 'account'

        request_url = self.uri + method_type + '/' + method + '?'

        if method_type != 'public':
            request_url += 'apikey=' + self.api_key.decode() + "&nonce=" + nonce + '&'

        request_url += urlencode(options)
        signature = hmac.new(
            self.secret,
            request_url.encode(),
            hashlib.sha512,
        ).hexdigest()
        self.session.headers.update({'apisign': signature})
        log.debug('Bittrex API query', request_url=request_url)
        response = self.session.get(request_url)

        if response.status_code != 200:
            raise RemoteError(
                f'Bittrex query responded with error status code: {response.status_code}'
                f' and text: {response.text}',
            )

        try:
            json_ret = rlk_jsonloads_dict(response.text)
        except JSONDecodeError:
            raise RemoteError(f'Bittrex returned invalid JSON response: {response.text}')

        if json_ret['success'] is not True:
            raise RemoteError(json_ret['message'])
        return json_ret['result']

    def get_btc_price(self, asset: Asset) -> Optional[FVal]:
        if asset == 'BTC':
            return None
        btc_price = None
        btc_pair = 'BTC-' + str(asset)
        for market in self.markets:
            if market['MarketName'] == btc_pair:
                btc_price = FVal(market['Last'])
                break

        return btc_price

    def get_currencies(self) -> List[Dict[str, Any]]:
        """Gets a list of all currencies supported by Bittrex"""
        result = self.api_query('getcurrencies')
        # We know this API call returns a list
        assert isinstance(result, List)
        return result

    @cache_response_timewise(CACHE_RESPONSE_FOR_SECS)
    def query_balances(self) -> Tuple[Optional[dict], str]:
        try:
            self.markets = self.api_query('getmarketsummaries')
            resp = self.api_query('getbalances')
        except RemoteError as e:
            msg = (
                'Bittrex API request failed. Could not reach bittrex due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        returned_balances = dict()
        for entry in resp:
            try:
                asset = asset_from_bittrex(entry['Currency'])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported bittrex asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            asset_btc_price = self.get_btc_price(asset)
            usd_price = self.inquirer.find_usd_price(
                asset=asset,
                asset_btc_price=asset_btc_price,
            )

            balance = dict()
            balance['amount'] = FVal(entry['Balance'])
            balance['usd_value'] = FVal(balance['amount']) * usd_price
            returned_balances[asset] = balance

            log.debug(
                'bittrex balance query result',
                sensitive_log=True,
                currency=asset,
                amount=balance['amount'],
                usd_value=balance['usd_value'],
            )

        return returned_balances, ''

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
            market: Optional[TradePair] = None,
            count: Optional[int] = None,
    ) -> List:

        options: Dict[str, Union[str, int]] = dict()
        cache = self.check_trades_cache(start_ts, end_at_least_ts)
        cache = cast(List, cache)
        if market is not None:
            options['market'] = world_pair_to_bittrex(market)
        elif cache is not None:
            return cache

        if count is not None:
            options['count'] = count
        order_history = self.api_query('getorderhistory', options)
        log.debug('binance order history result', results_num=len(order_history))

        returned_history = list()
        for order in order_history:
            order_timestamp = createTimeStamp(order['TimeStamp'], formatstr="%Y-%m-%dT%H:%M:%S.%f")
            if start_ts is not None and order_timestamp < start_ts:
                continue
            if end_ts is not None and order_timestamp > end_ts:
                break
            order['TimeStamp'] = order_timestamp
            returned_history.append(order)

        self.update_trades_cache(returned_history, start_ts, end_ts)
        return returned_history
