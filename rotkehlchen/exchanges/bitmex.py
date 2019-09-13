import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

from rotkehlchen import typing
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, Exchange, MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_fee
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import cache_response_timewise, iso8601ts_to_timestamp, satoshis_to_btc
from rotkehlchen.utils.serialization import rlk_jsonloads

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITMEX_PRIVATE_ENDPOINTS = (
    'user',
    'user/wallet',
    'user/walletHistory',
)


def bitmex_to_world(symbol: str) -> Asset:
    if symbol == 'XBt':
        return A_BTC
    return Asset(symbol)


def trade_from_bitmex(bitmex_trade: Dict) -> MarginPosition:
    """Turn a bitmex trade returned from bitmex trade history to our common trade
    history format. This only returns margin positions as bitmex only deals in
    margin trading"""
    close_time = iso8601ts_to_timestamp(bitmex_trade['transactTime'])
    profit_loss = satoshis_to_btc(FVal(bitmex_trade['amount']))
    currency = bitmex_to_world(bitmex_trade['currency'])
    notes = bitmex_trade['address']
    assert currency == 'BTC', 'Bitmex trade should only deal in BTC'

    log.debug(
        'Processing Bitmex Trade',
        sensitive_log=True,
        timestamp=close_time,
        profit_loss=profit_loss,
        currency=currency,
        notes=notes,
    )

    return MarginPosition(
        exchange='bitmex',
        open_time=None,
        close_time=close_time,
        profit_loss=profit_loss,
        pl_currency=A_BTC,
        notes=notes,
    )


class Bitmex(ExchangeInterface):
    def __init__(
            self,
            api_key: typing.ApiKey,
            secret: typing.ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super(Bitmex, self).__init__('bitmex', api_key, secret, database)
        self.uri = 'https://bitmex.com'
        self.session.headers.update({'api-key': api_key})  # type: ignore
        self.msg_aggregator = msg_aggregator

    def first_connection(self):
        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self._api_query('get', 'user')
        except RemoteError as e:
            error = str(e)
            if 'Invalid API Key' in error:
                return False, 'Provided API key is invalid'
            elif 'Signature not valid' in error:
                return False, 'Provided API secret is invalid'
            else:
                raise
        return True, ''

    def _generate_signature(self, verb: str, path: str, expires: int, data: str = ''):
        signature = hmac.new(
            self.secret,
            (verb.upper() + path + str(expires) + data).encode(),
            hashlib.sha256,
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
            request_path = request_path_no_args
        else:
            request_path = request_path_no_args + '?' + urlencode(options)

        if path in BITMEX_PRIVATE_ENDPOINTS:
            self._generate_signature(
                verb=verb,
                path=request_path,
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
        log.debug('Bitmex API Query', verb=verb, request_url=request_url)

        response = getattr(self.session, verb)(request_url, data=data)

        if response.status_code not in (200, 401):
            raise RemoteError(
                'Bitmex api request for {} failed with HTTP status code {}'.format(
                    response.url,
                    response.status_code,
                ),
            )

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError:
            raise RemoteError('Bitmex returned invalid JSON response')

        if isinstance(json_ret, dict) and 'error' in json_ret:
            raise RemoteError(json_ret['error']['message'])

        return json_ret

    def _api_query_dict(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Dict:
        result = self._api_query(verb, path, options)
        assert isinstance(result, Dict)
        return result

    def _api_query_list(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> List:
        result = self._api_query(verb, path, options)
        assert isinstance(result, List)
        return result

    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:

        resp = self._api_query_dict('get', 'user/wallet', {'currency': 'XBt'})
        # Bitmex shows only BTC balance
        returned_balances = dict()
        usd_price = Inquirer().find_usd_price(A_BTC)
        # result is in satoshis
        amount = satoshis_to_btc(FVal(resp['amount']))
        usd_value = amount * usd_price

        returned_balances[A_BTC] = dict(
            amount=amount,
            usd_value=usd_value,
        )
        log.debug(
            'Bitmex balance query result',
            sensitive_log=True,
            currency='BTC',
            amount=amount,
            usd_value=usd_value,
        )

        return returned_balances, ''

    def query_online_trade_history(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
    ) -> List[MarginPosition]:

        # We know user/walletHistory returns a list
        resp = self._api_query_list('get', 'user/walletHistory')
        log.debug('Bitmex trade history query', results_num=len(resp))

        margin_trades = []
        for tx in resp:
            if tx['timestamp'] is None:
                timestamp = None
            else:
                timestamp = iso8601ts_to_timestamp(tx['timestamp'])
            if tx['transactType'] != 'RealisedPNL':
                continue
            if timestamp and timestamp < start_ts:
                continue
            if timestamp and timestamp > end_ts:
                continue
            margin_trades.append(trade_from_bitmex(tx))

        return margin_trades

    def query_deposits_withdrawals(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
    ) -> List:
        resp = self._api_query_list('get', 'user/walletHistory')

        log.debug('Bitmex deposit/withdrawals query', results_num=len(resp))

        movements = list()
        for movement in resp:
            try:
                transaction_type = movement['transactType']
                if transaction_type == 'Deposit':
                    transaction_type = 'deposit'
                elif transaction_type == 'Withdrawal':
                    transaction_type = 'withdrawal'
                else:
                    continue

                timestamp = iso8601ts_to_timestamp(movement['timestamp'])
                if timestamp < start_ts:
                    continue
                if timestamp > end_ts:
                    continue

                asset = bitmex_to_world(movement['currency'])
                amount = deserialize_asset_amount(movement['amount'])
                fee = deserialize_fee(movement['fee'])
                # bitmex has negative numbers for withdrawals
                if amount < 0:
                    amount *= -1

                if asset == A_BTC:
                    # bitmex stores amounts in satoshis
                    amount = satoshis_to_btc(amount)
                    fee = satoshis_to_btc(fee)

                movements.append(AssetMovement(
                    exchange=Exchange.BITMEX,
                    category=transaction_type,
                    timestamp=timestamp,
                    asset=asset,
                    amount=amount,
                    fee=fee,
                ))
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found bitmex deposit/withdrawal with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Unexpected data encountered during deserialization of a bitmex '
                    f'asset movement. Check logs for details and open a bug report.',
                )
                log.error(
                    f'Unexpected data encountered during deserialization of bitmex '
                    f'asset_movement {movement}. Error was: {str(e)}',
                )
                continue
        return movements
