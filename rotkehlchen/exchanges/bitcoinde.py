import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, Location, Price, Trade, TradePair
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import iso8601ts_to_timestamp
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def bitcoin_pair_to_world(pair: str) -> Tuple[Asset, Asset]:
    tx_asset = Asset(pair[:3].upper())
    native_asset = Asset(pair[3:].upper())
    return tx_asset, native_asset


def trade_from_bitcoinde(raw_trade: Dict) -> Trade:

    if raw_trade['state'] != 1:
        # We only want to deal with completed trades
        return None

    try:
        timestamp = deserialize_timestamp_from_date(raw_trade['successfully_finished_at'], 'iso8601', 'bitcoinde')
    except KeyError:
        # For very old trades (2013) bitcoin.de does not return 'successfully_finished_at'
        timestamp = deserialize_timestamp_from_date(raw_trade['trade_marked_as_paid_at'], 'iso8601', 'bitcoinde')
    trade_type = deserialize_trade_type(raw_trade['type'])
    tx_amount = raw_trade['amount_currency_to_trade']

    native_amount = raw_trade['volume_currency_to_pay']
    tx_asset, native_asset = bitcoin_pair_to_world(raw_trade['trading_pair'])
    pair = TradePair(f'{tx_asset.identifier}_{native_asset.identifier}')
    amount = tx_amount
    rate = Price(native_amount / tx_amount)
    fee_amount = deserialize_fee(raw_trade['fee_currency_to_pay'])
    fee_asset = Asset('EUR')

    return Trade(
        timestamp=timestamp,
        location=Location.BITCOINDE,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(raw_trade['trade_id']),
    )


class Bitcoinde(ExchangeInterface):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super(Bitcoinde, self).__init__('bitcoin.de', api_key, secret, database)
        self.uri = 'https://api.bitcoin.de'
        self.session.headers.update({'x-api-key': api_key})
        self.msg_aggregator = msg_aggregator

    def _generate_signature(self, request_type: str, url: str, nonce: str) -> str:
        md5_empty = 'd41d8cd98f00b204e9800998ecf8427e'  # this is md5('')
        signed_data = '#'.join([request_type, url, self.api_key, nonce, md5_empty]).encode()
        signature = hmac.new(
            self.secret,
            signed_data,
            hashlib.sha256,
        ).hexdigest()
        self.session.headers.update({
            'x-api-signature': signature,
        })
        return signature

    def _api_query(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Union[List, Dict]:
        """
        Queries Bitcoin.de with the given verb for the given path and options
        """
        assert verb in ('get', 'post', 'push'), (
            'Given verb {} is not a valid HTTP verb'.format(verb)
        )

        # 20 seconds expiration
        expires = int(time.time()) + 20

        request_path_no_args = '/v4/' + path

        data = ''
        if not options:
            request_path = request_path_no_args
        else:
            request_path = request_path_no_args + '?' + urlencode(options)

        nonce = str(int(time.time() * 1000))
        request_url = self.uri + request_path

        self._generate_signature(
            request_type=verb.upper(),
            url=request_url,
            nonce=nonce
        )

        self.session.headers.update({
            'x-api-nonce': nonce,
        })
        if data != '':
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        log.debug('Bitcoin.de API Query', verb=verb, request_url=request_url)

        response = getattr(self.session, verb)(request_url, data=data)

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError:
            raise RemoteError('Bitmex returned invalid JSON response')

        if response.status_code not in (200, 401):
            if isinstance(json_ret, dict) and 'errors' in json_ret:
                raise RemoteError(json_ret['errors'])
            else:
                raise RemoteError(
                    'Bitmex api request for {} failed with HTTP status code {}'.format(
                        response.url,
                        response.status_code,
                    ),
                )

        return json_ret

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

            if not 'page' in resp:
                break

            if resp['page']['current'] >= resp['page']['last']:
                break

            page = resp['page']['current'] + 1

        log.debug('Bitcoin.de trade history query', results_num=len(resp_trades))

        trades = []
        for tx in resp_trades:
            try:
                timestamp = iso8601ts_to_timestamp(tx['successfully_finished_at'])
            except KeyError:
                # For very old trades (2013) bitcoin.de does not return 'successfully_finished_at'
                timestamp = iso8601ts_to_timestamp(tx['trade_marked_as_paid_at'])

            if tx['state'] != 1:
                continue
            if timestamp and timestamp < start_ts:
                continue
            if timestamp and timestamp > end_ts:
                continue
            trades.append(trade_from_bitcoinde(tx))

        return trades
