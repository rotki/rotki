import hashlib
import base64
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Any
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import Location, Price, Trade, TradePair
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import iso8601ts_to_timestamp
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def iconomi_asset(asset: str) -> Asset:
    return Asset(asset.upper())


def iconomi_pair_to_world(pair: str) -> Tuple[Asset, Asset]:
    tx_asset = iconomi_asset(pair[:3])
    native_asset = iconomi_asset(pair[3:])
    return tx_asset, native_asset


def trade_from_iconomi(raw_trade: Dict) -> Trade:

    timestamp = deserialize_timestamp_from_date(
        raw_trade['successfully_finished_at'],
        'iso8601',
        'iconomi',
    )
    trade_type = deserialize_trade_type(raw_trade['type'])
    tx_amount = raw_trade['amount_currency_to_trade']

    native_amount = raw_trade['volume_currency_to_pay']
    tx_asset, native_asset = iconomi_pair_to_world(raw_trade['trading_pair'])
    pair = TradePair(f'{tx_asset.identifier}_{native_asset.identifier}')
    amount = tx_amount
    rate = Price(native_amount / tx_amount)
    fee_amount = deserialize_fee(raw_trade['fee_currency_to_pay'])
    fee_asset = Asset('EUR')

    return Trade(
        timestamp=timestamp,
        location=Location.ICONOMI,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(raw_trade['trade_id']),
    )


class Iconomi(ExchangeInterface):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super(Iconomi, self).__init__('iconomi.com', api_key, secret, database)
        self.uri = 'https://api.iconomi.com'
        self.session.headers.update({'ICN-API-KEY': api_key})
        self.msg_aggregator = msg_aggregator

    def _generate_signature(self, request_type: str, request_path: str, timestamp: str) -> str:
        signed_data = ''.join([timestamp, request_type.upper(), request_path, '']).encode()
        signature = hmac.new(
            self.secret,
            signed_data,
            hashlib.sha512,
        )
        self.session.headers.update({
            'ICN-SIGN': base64.b64encode(signature.digest()).decode()
        })
        return signature

    def _api_query(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Dict:
        """
        Queries ICONOMI with the given verb for the given path and options
        """
        assert verb in ('get', 'post', 'push'), (
            'Given verb {} is not a valid HTTP verb'.format(verb)
        )

        request_path_no_args = '/v1/' + path

        data = ''
        if not options:
            request_path = request_path_no_args
        else:
            request_path = request_path_no_args + '?' + urlencode(options)

        timestamp = str(int(time.time() * 1000))
        request_url = self.uri + request_path

        self._generate_signature(
            request_type=verb.upper(),
            request_path=request_path,
            timestamp=timestamp,
        )

        self.session.headers.update({
            'ICN-TIMESTAMP': timestamp,
        })
        if data != '':
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        log.debug('ICONOMI API Query', verb=verb, request_url=request_url)

        response = getattr(self.session, verb)(request_url, data=data)

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError:
            raise RemoteError('ICONOMI returned invalid JSON response')

        if response.status_code not in (200, 201):
            if isinstance(json_ret, dict) and 'message' in json_ret:
                raise RemoteError(json_ret['message'])
            else:
                raise RemoteError(
                    'ICONOMI api request for {} failed with HTTP status code {}'.format(
                        response.url,
                        response.status_code,
                    ),
                )

        if not isinstance(json_ret, dict):
            raise RemoteError('ICONOMI returned invalid non-dict response')

        return json_ret

    def query_balances(self, **kwargs: Any) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        balances = {}
        resp_info = self._api_query('get', 'user/balance')

        for balance_info in (resp_info['assetList'] + resp_info['daaList']):
            ticker = balance_info['ticker']
            try:
                asset = iconomi_asset(ticker)
                balances[iconomi_asset(ticker)] = {
                    'amount': balance_info['balance'],
                    'usd_value': balance_info['value']
                }
            except UnknownAsset:
                log.warning('Ignoring unsupported ICONOMI asset "%s"', ticker)

        return (balances, "")

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List:

        page = 1
        resp_trades = []

        while True:
            resp = self._api_query('get', 'trades', {'state': 1, 'page': page})
            resp_trades.extend(resp['trades'])

            if 'page' not in resp:
                break

            if resp['page']['current'] >= resp['page']['last']:
                break

            page = resp['page']['current'] + 1

        log.debug('ICONOMI trade history query', results_num=len(resp_trades))

        trades = []
        for tx in resp_trades:
            try:
                timestamp = iso8601ts_to_timestamp(tx['successfully_finished_at'])
            except KeyError:
                # For very old trades (2013) iconomi.com does not return 'successfully_finished_at'
                timestamp = iso8601ts_to_timestamp(tx['trade_marked_as_paid_at'])

            if tx['state'] != 1:
                continue
            if timestamp and timestamp < start_ts:
                continue
            if timestamp and timestamp > end_ts:
                continue
            trades.append(trade_from_iconomi(tx))

        return trades
