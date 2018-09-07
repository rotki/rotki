import time
import hmac
import hashlib
from urllib.parse import urlencode
from json.decoder import JSONDecodeError

from typing import Dict, Tuple, Optional, Union, List
from rotkehlchen.utils import (
    rlk_jsonloads,
    cache_response_timewise,
)
from rotkehlchen.exchange import Exchange
from rotkehlchen.order_formatting import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.errors import RemoteError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen import typing

import logging
logger = logging.getLogger(__name__)

BITMEX_PRIVATE_ENDPOINTS = (
    'user',
    'user/wallet'
)


def trade_from_bitmex(bittrex_trade: Dict) -> Trade:
    """Turn a bitmex trade returned from bittrex trade history to our common trade
    history format"""
    # TODO
    return None
    # amount = FVal(bittrex_trade['Quantity']) - FVal(bittrex_trade['QuantityRemaining'])
    # rate = FVal(bittrex_trade['PricePerUnit'])
    # order_type = bittrex_trade['OrderType']
    # bittrex_price = FVal(bittrex_trade['Price'])
    # bittrex_commission = FVal(bittrex_trade['Commission'])
    # pair = bittrex_pair_to_world(bittrex_trade['Exchange'])
    # base_currency = get_pair_position(pair, 'first')
    # if order_type == 'LIMIT_BUY':
    #     order_type = 'buy'
    #     cost = bittrex_price + bittrex_commission
    #     fee = bittrex_commission
    # elif order_type == 'LIMIT_SEL':
    #     order_type = 'sell'
    #     cost = bittrex_price - bittrex_commission
    #     fee = bittrex_commission
    # else:
    #     raise ValueError('Got unexpected order type "{}" for bittrex trade'.format(order_type))

    # return Trade(
    #     timestamp=bittrex_trade['TimeStamp'],
    #     pair=pair,
    #     type=order_type,
    #     rate=rate,
    #     cost=cost,
    #     cost_currency=base_currency,
    #     fee=fee,
    #     fee_currency=base_currency,
    #     amount=amount,
    #     location='bitmex'
    # )


class Bitmex(Exchange):
    def __init__(
            self,
            api_key: typing.ApiKey,
            secret: typing.ApiSecret,
            inquirer: Inquirer,
            data_dir: typing.FilePath
    ):
        super(Bitmex, self).__init__('bitmex', api_key, secret, data_dir)
        self.uri = 'https://bitmex.com'
        self.inquirer = inquirer
        self.session.headers.update({'api-key': api_key})

    def first_connection(self):
        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self._api_query('get', 'user')
        except RemoteError as e:
            error = str(e)
            if error == 'Invalid API Key.':
                return False, 'Provided API key is invalid'
            elif error == 'Signature not valid.':
                return False, 'Provided API secret is invalid'
            else:
                raise
        return True, ''

    def _generate_signature(self, verb: str, path: str, expires: int, data: str = ''):
        signature = hmac.new(
            self.secret,
            (verb.upper() + path + str(expires) + data).encode(),
            hashlib.sha256
        ).hexdigest()
        self.session.headers.update({
            'api-signature': signature,
        })
        return signature

    def _api_query(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Union[List, Dict]:
        """
        Queries Bitmex with the given verb for the given path and options
        """
        assert verb in ('get', 'post', 'push'), (
            'Given verb {} is not a valid HTTP verb'.format(verb)
        )

        # 20 seconds expiration
        expires = int(time.time()) + 20

        request_path_no_args = '/api/v1/' + path

        data = ''
        if not options:
            options = {}
            request_path = request_path_no_args
        else:
            request_path = request_path_no_args + '?' + urlencode(options)

        if path in BITMEX_PRIVATE_ENDPOINTS:
            self._generate_signature(
                verb=verb,
                path=request_path_no_args,
                expires=expires,
                data=data,
            )

        self.session.headers.update({
            'api-expires': str(expires),
        })
        if data != '':
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        request_url = self.uri + request_path
        response = getattr(self.session, verb)(request_url, data=data)

        if response.status_code not in (200, 401):
            raise RemoteError(
                'Bitmex api request for {} failed with HTTP status code {}'.format(
                    response.url,
                    response.status_code,
                )
            )

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError:
            raise RemoteError('Bitmex returned invalid JSON response')

        if 'error' in json_ret:
            raise RemoteError(json_ret['error']['message'])

        return json_ret

    def get_btc_price(self, asset: typing.BlockchainAsset) -> Optional[FVal]:
        if asset == 'BTC':
            return None
        btc_price = None
        btc_pair = 'BTC-' + asset
        for market in self.markets:
            if market['MarketName'] == btc_pair:
                btc_price = FVal(market['Last'])
                break

        if btc_price is None:
            raise ValueError('Bittrex: Could not find BTC market for "{}"'.format(asset))

        return btc_price

    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:
        try:
            resp = self._api_query('get', 'user/wallet', {'currency': 'XBt'})
        except RemoteError as e:
            msg = (
                'Bitmex API request failed. Could not reach bitmex due '
                'to {}'.format(e)
            )
            logger.error(msg)
            return None, msg

        # Bitmex shows only BTC balance
        returned_balances = dict()
        usd_price = self.inquirer.find_usd_price('BTC')
        amount = FVal(resp['amount'])
        returned_balances['BTC'] = dict(
            amount=amount,
            usd_value=amount * usd_price
        )

        return returned_balances, ''

    def query_trade_history(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
            market: Optional[str] = None,
            count: Optional[int] = None,
    ) -> List:

        raise NotImplementedError(
            'Querying trade history is not yet implemented for bitmex'
        )
        return list()
