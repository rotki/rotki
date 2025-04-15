import hashlib
import hmac
import json
import logging
import time
from collections.abc import Sequence
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bitcoinde
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Location, MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.events.structures.swap import SwapEvent, create_swap_events
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import ApiKey, ApiSecret, AssetAmount, ExchangeAuthCredentials, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# This corresponds to md5('') and is used in signature generation
MD5_EMPTY_STR = 'd41d8cd98f00b204e9800998ecf8427e'


def bitcoinde_pair_to_world(pair: str) -> tuple[AssetWithOracles, AssetWithOracles]:
    if len(pair) == 6:
        tx_asset = asset_from_bitcoinde(pair[:3])
        native_asset = asset_from_bitcoinde(pair[3:])
    elif len(pair) in {7, 8}:
        tx_asset = asset_from_bitcoinde(pair[:4])
        native_asset = asset_from_bitcoinde(pair[4:])
    else:
        raise DeserializationError(f'Could not parse pair: {pair}')
    return tx_asset, native_asset


class Bitcoinde(ExchangeInterface):
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
            location=Location.BITCOINDE,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://api.bitcoin.de'
        self.session.headers.update({'x-api-key': api_key})

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'x-api-key': credentials.api_key})
        return changed

    def _generate_signature(self, request_type: str, url: str, nonce: str) -> str:
        signed_data = f'{request_type}#{url}#{self.api_key}#{nonce}#{MD5_EMPTY_STR}'.encode()
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
            verb: Literal['get', 'post'],
            path: str,
            options: dict | None = None,
    ) -> dict:
        """
        Queries Bitcoin.de with the given verb for the given path and options
        """
        assert verb in {'get', 'post'}, (
            f'Given verb {verb} is not a valid HTTP verb'
        )

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
            nonce=nonce,
        )

        headers = {
            'x-api-nonce': nonce,
        }
        if data != '':
            headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        log.debug('Bitcoin.de API Query', verb=verb, request_url=request_url)

        try:
            response = getattr(self.session, verb)(request_url, data=data, headers=headers)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Bitcoin.de API request failed due to {e!s}') from e

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as exc:
            raise RemoteError('Bitcoin.de returned invalid JSON response') from exc

        if response.status_code not in {200, 401}:
            if isinstance(json_ret, dict) and 'errors' in json_ret:
                for error in json_ret['errors']:
                    if error.get('field') == 'X-API-KEY' and error.get('code') == 1:
                        raise RemoteError('Provided API Key is in invalid Format')

                    if error.get('code') == 3:
                        raise RemoteError('Provided API Key is invalid')

                raise RemoteError(json_ret['errors'])

            raise RemoteError(
                f'Bitcoin.de api request for {response.url} failed '
                f'with HTTP status code {response.status_code}',
            )

        if not isinstance(json_ret, dict):
            raise RemoteError('Bitcoin.de returned invalid non-dict response')

        return json_ret

    def validate_api_key(self) -> tuple[bool, str]:
        """
        Validates that the Bitcoin.de API key is good for usage in rotki
        """

        try:
            self._api_query('get', 'account')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        assets_balance: dict[AssetWithOracles, Balance] = {}
        try:
            resp_info = self._api_query('get', 'account')
        except RemoteError as e:
            msg = (
                'Bitcoin.de request failed. Could not reach bitcoin.de due '
                f'to {e}'
            )
            log.error(msg)
            return None, msg

        log.debug(f'Bitcoin.de account response: {resp_info}')
        for currency, balance in resp_info['data']['balances'].items():
            try:
                asset = asset_from_bitcoinde(currency)
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Bitcoin.de balance entry due to inability to '
                    f'query USD price: {e!s}. Skipping balance entry',
                )
                continue

            try:
                amount = deserialize_fval(balance['total_amount'])
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Bitcoin.de {asset} balance entry due to inability to '
                    f'deserialize the amount due to {e!s}. Skipping balance entry',
                )
                continue

            assets_balance[asset] = Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return assets_balance, ''

    def _deserialize_trade(self, raw_trade: dict) -> list[SwapEvent]:
        """Convert bitcoin.de raw trade data to a list of SwapEvents.

        May raise:
        - DeserializationError
        - UnknownAsset
        - KeyError
        """
        # For very old trades (2013) bitcoin.de does not return 'successfully_finished_at'
        raw_timestamp = raw_trade.get('successfully_finished_at', raw_trade['trade_marked_as_paid_at'])  # noqa: E501
        tx_amount = deserialize_fval(raw_trade['amount_currency_to_trade'])
        native_amount = deserialize_fval(raw_trade['volume_currency_to_pay'])
        tx_asset, native_asset = bitcoinde_pair_to_world(raw_trade['trading_pair'])
        if raw_trade['type'] == 'buy':
            spend_asset, spend_amount, receive_asset, receive_amount = native_asset, native_amount, tx_asset, tx_amount  # noqa: E501
        else:  # sell
            spend_asset, spend_amount, receive_asset, receive_amount = tx_asset, tx_amount, native_asset, native_amount  # noqa: E501

        return create_swap_events(
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_date(
                date=raw_timestamp,
                formatstr='iso8601',
                location='bitcoinde',
            )),
            location=self.location,
            spend=AssetAmount(asset=spend_asset, amount=spend_amount),
            receive=AssetAmount(asset=receive_asset, amount=receive_amount),
            fee=AssetAmount(asset=A_EUR, amount=deserialize_fval_or_zero(raw_trade['fee_currency_to_pay'])),  # noqa: E501
            location_label=self.name,
            unique_id=raw_trade['trade_id'],
        )

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:

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

        log.debug('Bitcoin.de trade history query', results_num=len(resp_trades))
        events = []
        for tx in resp_trades:
            log.debug(f'Processing raw Bitcoin.de trade: {tx}')
            try:
                timestamp = iso8601ts_to_timestamp(tx['successfully_finished_at'])
            except KeyError:
                # For very old trades (2013) bitcoin.de does not return 'successfully_finished_at'
                timestamp = iso8601ts_to_timestamp(tx['trade_marked_as_paid_at'])

            if tx['state'] != 1:
                continue
            if timestamp < start_ts or timestamp > end_ts:
                continue
            try:
                events.extend(swap_events := self._deserialize_trade(raw_trade=tx))
                log.debug(f'Deserialized swap events from Bitcoin.de: {swap_events}')
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='trade',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a Bitcoin.de trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a Bitcoin.de trade',
                    trade=tx,
                    error=msg,
                )
                continue

        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for bitcoinde
