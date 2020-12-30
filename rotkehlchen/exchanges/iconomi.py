import base64
import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from requests.exceptions import ReadTimeout

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import Location, Price, Trade, TradePair, TradeType
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ApiKey, ApiSecret, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

SUPPORTED_FUND_TICKERS = ('BLX',)


def iconomi_asset(asset: str) -> Asset:
    return Asset(asset.upper())


def iconomi_pair_to_world(pair: str) -> Tuple[Asset, Asset]:
    tx_asset = iconomi_asset(pair[:3])
    native_asset = iconomi_asset(pair[3:])
    return tx_asset, native_asset


def trade_from_iconomi(raw_trade: Dict) -> Trade:

    timestamp = raw_trade['timestamp']

    if (
        raw_trade['type'] == 'buy_fund' and
        raw_trade['target_ticker'] not in SUPPORTED_FUND_TICKERS
    ):
        raise UnknownAsset(raw_trade['target_ticker'])

    if (
        raw_trade['type'] == 'sell_fund' and
        raw_trade['source_ticker'] not in SUPPORTED_FUND_TICKERS
    ):
        raise UnknownAsset(raw_trade['target_ticker'])

    if raw_trade['type'] in ('buy_asset', 'buy_fund'):
        trade_type = TradeType.BUY
        tx_asset = Asset(raw_trade['target_ticker'])
        tx_amount = raw_trade['target_amount']
        native_asset = Asset(raw_trade['source_ticker'])
        native_amount = raw_trade['source_amount']
    else:
        trade_type = TradeType.SELL
        tx_asset = Asset(raw_trade['source_ticker'])
        tx_amount = raw_trade['source_amount']
        native_amount = raw_trade['target_amount']
        native_asset = Asset(raw_trade['target_ticker'])

    pair = TradePair(f'{tx_asset.identifier}_{native_asset.identifier}')
    amount = tx_amount
    rate = Price(native_amount / tx_amount)
    fee_amount = raw_trade['fee_amount']
    fee_asset = Asset(raw_trade['fee_ticker'])

    return Trade(
        timestamp=timestamp,
        location=Location.ICONOMI,
        pair=pair,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(raw_trade['transactionId']),
    )


class Iconomi(ExchangeInterface):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__('iconomi', api_key, secret, database)
        self.uri = 'https://api.iconomi.com'
        self.session.headers.update({'ICN-API-KEY': api_key})
        self.msg_aggregator = msg_aggregator

    def _generate_signature(self, request_type: str, request_path: str, timestamp: str) -> None:
        signed_data = ''.join([timestamp, request_type.upper(), request_path, '']).encode()
        signature = hmac.new(
            self.secret,
            signed_data,
            hashlib.sha512,
        )
        self.session.headers.update({
            'ICN-SIGN': base64.b64encode(signature.digest()).decode(),
        })

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
            request_path=request_path_no_args,
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

        try:
            response = getattr(self.session, verb)(request_url, data=data, timeout=30)
        except ReadTimeout as exc:
            raise RemoteError('Read timeout') from exc

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError as exc:
            raise RemoteError('ICONOMI returned invalid JSON response') from exc

        if response.status_code not in (200, 201):
            if isinstance(json_ret, dict) and 'message' in json_ret:
                raise RemoteError(json_ret['message'])

            raise RemoteError(
                'ICONOMI api request for {} failed with HTTP status code {}'.format(
                    response.url,
                    response.status_code,
                ),
            )

        if not isinstance(json_ret, dict):
            raise RemoteError('ICONOMI returned invalid non-dict response')

        return json_ret

    def validate_api_key(self) -> Tuple[bool, str]:
        "Validates that the ICONOMI API key is good for usage in Rotki"

        try:
            self._api_query('get', 'user/balance')
            return True, ""

        except RemoteError:
            return False, 'Provided API Key is invalid'

    def query_balances(self, **kwargs: Any) -> Tuple[Optional[Dict[Asset, Dict[str, Any]]], str]:
        balances = {}
        resp_info = self._api_query('get', 'user/balance')

        for balance_info in resp_info['assetList']:
            ticker = balance_info['ticker']
            try:
                asset = iconomi_asset(ticker)
                balances[asset] = {
                    'amount': balance_info['balance'],
                    'usd_value': balance_info['value'],
                }
            except UnknownAsset:
                self.msg_aggregator.add_warning(
                    f'Found unsupported ICONOMI asset {ticker}. '
                    f' Ignoring its balance query.',
                )

        for balance_info in resp_info['daaList']:
            ticker = balance_info['ticker']
            try:
                if ticker not in SUPPORTED_FUND_TICKERS:
                    raise UnknownAsset(ticker)

                asset = iconomi_asset(ticker)
                balances[asset] = {
                    'amount': balance_info['balance'],
                    'usd_value': balance_info['value'],
                }
            except UnknownAsset:
                self.msg_aggregator.add_warning(
                    f'Found unsupported ICONOMI fund {ticker}. '
                    f' Ignoring its balance query.',
                )

        return (balances, "")

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List:

        page = 0
        all_transactions = []

        while True:
            resp = self._api_query('get', 'user/activity', {"pageNumber": str(page)})

            if len(resp['transactions']) == 0:
                break

            all_transactions.extend(resp['transactions'])
            page += 1

        log.debug('ICONOMI trade history query', results_num=len(all_transactions))

        trades = []
        for tx in all_transactions:
            timestamp = tx['timestamp']
            if timestamp and timestamp < start_ts:
                continue
            if timestamp and timestamp > end_ts:
                continue

            if tx['type'] in ('buy_asset', 'sell_asset', 'buy_fund', 'sell_fund'):
                try:
                    trades.append(trade_from_iconomi(tx))
                except UnknownAsset:
                    log.warning('Ignoring transaction %s because of unsupported asset', str(tx))

        return trades
