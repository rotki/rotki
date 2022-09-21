import base64
import hashlib
import hmac
import json
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import UNSUPPORTED_ICONOMI_ASSETS, asset_from_iconomi
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_AUST
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Location,
    MarginPosition,
    Price,
    Trade,
    TradeType,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_fval,
)
from rotkehlchen.types import ApiKey, ApiSecret, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def trade_from_iconomi(raw_trade: Dict) -> Trade:
    """Turn an iconomi trade entry to our own trade format

    May raise:
    - UnknownAsset
    - DeserializationError
    - KeyError
    """

    timestamp = raw_trade['timestamp']

    if raw_trade['type'] == 'buy_asset':
        trade_type = TradeType.BUY
        tx_asset = asset_from_iconomi(raw_trade['target_ticker'])
        tx_amount = deserialize_asset_amount(raw_trade['target_amount'])
        native_asset = asset_from_iconomi(raw_trade['source_ticker'])
        native_amount = deserialize_asset_amount(raw_trade['source_amount'])
    elif raw_trade['type'] == 'sell_asset':
        trade_type = TradeType.SELL
        tx_asset = asset_from_iconomi(raw_trade['source_ticker'])
        tx_amount = deserialize_asset_amount(raw_trade['source_amount'])
        native_amount = deserialize_asset_amount(raw_trade['target_amount'])
        native_asset = asset_from_iconomi(raw_trade['target_ticker'])

    amount = tx_amount
    rate = Price(native_amount / tx_amount)
    fee_amount = deserialize_fee(raw_trade['fee_amount'])
    fee_asset = asset_from_iconomi(raw_trade['fee_ticker'])
    return Trade(
        timestamp=timestamp,
        location=Location.ICONOMI,
        base_asset=tx_asset,
        quote_asset=native_asset,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee_amount,
        fee_currency=fee_asset,
        link=str(raw_trade['transactionId']),
    )


class Iconomi(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.ICONOMI,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.uri = 'https://api.iconomi.com'
        self.msg_aggregator = msg_aggregator

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        return changed

    def _generate_signature(self, request_type: str, request_path: str, timestamp: str) -> str:
        signed_data = ''.join([timestamp, request_type.upper(), request_path, '']).encode()
        signature = hmac.new(
            self.secret,
            signed_data,
            hashlib.sha512,
        )
        return base64.b64encode(signature.digest()).decode()

    def _api_query(
            self,
            verb: Literal['get', 'post'],
            path: str,
            options: Optional[Dict] = None,
            authenticated: bool = True,
    ) -> Any:
        """
        Queries ICONOMI with the given verb for the given path and options
        """
        assert verb in ('get', 'post'), (
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

        headers = {}
        if authenticated:
            signature = self._generate_signature(
                request_type=verb.upper(),
                request_path=request_path_no_args,
                timestamp=timestamp,
            )
            headers.update({
                'ICN-SIGN': signature,
                # set api key only here since if given in non authenticated endpoint gives 400
                'ICN-API-KEY': self.api_key,
                'ICN-TIMESTAMP': timestamp,
            })

        if data != '':
            headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        log.debug('ICONOMI API Query', verb=verb, request_url=request_url)

        try:
            response = getattr(self.session, verb)(
                request_url,
                data=data,
                timeout=30,
                headers=headers,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'ICONOMI API request failed due to {str(e)}') from e

        try:
            json_ret = json.loads(response.text)
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

        return json_ret

    def validate_api_key(self) -> Tuple[bool, str]:
        """
        Validates that the ICONOMI API key is good for usage in rotki
        """

        try:
            self._api_query('get', 'user/balance')
            return True, ""

        except RemoteError:
            return False, 'Provided API Key is invalid'

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        assets_balance: Dict[AssetWithOracles, Balance] = {}
        try:
            resp_info = self._api_query('get', 'user/balance')
        except RemoteError as e:
            msg = (
                'ICONOMI API request failed. Could not reach ICONOMI due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        if resp_info['currency'] != 'USD':
            raise RemoteError('Iconomi API did not return values in USD')

        for balance_info in resp_info['assetList']:
            ticker = balance_info['ticker']
            try:
                asset = asset_from_iconomi(ticker)

                try:
                    usd_value = deserialize_fval(balance_info['value'], 'usd_value', 'iconomi')
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Skipping iconomi balance entry {balance_info} due to {msg}',
                    )
                    continue

                try:
                    amount = deserialize_asset_amount(balance_info['balance'])
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Skipping iconomi balance entry {balance_info} due to {msg}',
                    )
                    continue

                assets_balance[asset] = Balance(
                    amount=amount,
                    usd_value=usd_value,
                )
            except (UnknownAsset, UnsupportedAsset) as e:
                asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                self.msg_aggregator.add_warning(
                    f'Found {asset_tag} ICONOMI asset {ticker}. '
                    f' Ignoring its balance query.',
                )
                continue

        for balance_info in resp_info['daaList']:
            ticker = balance_info['ticker']

            if ticker == 'AUSTS':
                # The AUSTS strategy is 'ICONOMI Earn'. We know that this strategy holds its
                # value in Anchor UST (AUST). That's why we report the user balance for this
                # strategy as usd_value / AUST price.
                try:
                    aust_usd_price = Inquirer().find_usd_price(asset=A_AUST)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing ICONOMI balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                if aust_usd_price == ZERO:
                    self.msg_aggregator.add_error(
                        'Error processing ICONOMI balance entry because the USD price '
                        'for AUST was reported as 0. Skipping balance entry',
                    )
                    continue

                try:
                    usd_value = deserialize_fval(balance_info['value'], 'usd_value', 'iconomi')
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Skipping iconomi balance entry {balance_info} due to {msg}',
                    )
                    continue

                assets_balance[A_AUST.resolve_to_asset_with_oracles()] = Balance(
                    amount=usd_value / aust_usd_price,
                    usd_value=usd_value,
                )
            else:
                self.msg_aggregator.add_warning(
                    f'Found unsupported ICONOMI strategy {ticker}. '
                    f' Ignoring its balance query.',
                )

        return assets_balance, ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:

        page = 0
        all_transactions = []

        while True:
            resp = self._api_query('get', 'user/activity', {'pageNumber': str(page)})

            if len(resp['transactions']) == 0:
                break

            all_transactions.extend(resp['transactions'])
            page += 1

        log.debug('ICONOMI trade history query', results_num=len(all_transactions))

        trades = []
        for tx in all_transactions:
            timestamp = tx['timestamp']
            if timestamp < start_ts:
                continue
            if timestamp > end_ts:
                continue

            if tx['type'] in ('buy_asset', 'sell_asset'):
                try:
                    trades.append(trade_from_iconomi(tx))
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Ignoring an iconomi transaction because of unsupported '
                        f'asset {str(e)}')
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        'Error processing an iconomi transaction. Check logs '
                        'for details. Ignoring it.',
                    )
                    log.error(
                        'Error processing an iconomi transaction',
                        error=msg,
                        trade=tx,
                    )

        return trades, (start_ts, end_ts)

    def query_supported_tickers(
            self,
    ) -> List[str]:

        tickers = []
        resp = self._api_query('get', 'assets', authenticated=False)

        for asset_info in resp:
            if not asset_info['supported']:
                continue
            if asset_info['ticker'] in UNSUPPORTED_ICONOMI_ASSETS:
                continue
            tickers.append(asset_info['ticker'])

        return tickers

    def query_online_deposits_withdrawals(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[AssetMovement]:
        return []  # noop for iconomi

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for iconomi

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for iconomi
