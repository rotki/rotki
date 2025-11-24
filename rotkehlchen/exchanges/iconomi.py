import base64
import hashlib
import json
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_iconomi
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_AUST
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Location, MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_fval_or_zero
from rotkehlchen.types import ApiKey, ApiSecret, AssetAmount, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Iconomi(ExchangeInterface, SignatureGeneratorMixin):
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
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://api.iconomi.com'
        self.aust = A_AUST.resolve_to_asset_with_oracles()

    def _generate_signature(self, request_type: str, request_path: str, timestamp: str) -> str:
        signed_data = f'{timestamp}{request_type.upper()}{request_path}'
        signature_digest = self.generate_hmac_signature(
            message=signed_data,
            digest_algorithm=hashlib.sha512,
        )
        return base64.b64encode(bytes.fromhex(signature_digest)).decode()

    def _api_query(
            self,
            verb: Literal['get', 'post'],
            path: str,
            options: dict | None = None,
            authenticated: bool = True,
    ) -> Any:
        """
        Queries ICONOMI with the given verb for the given path and options
        """
        assert verb in {'get', 'post'}, (
            f'Given verb {verb} is not a valid HTTP verb'
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
            raise RemoteError(f'ICONOMI API request failed due to {e!s}') from e

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as exc:
            raise RemoteError('ICONOMI returned invalid JSON response') from exc

        if response.status_code not in {200, 201}:
            if isinstance(json_ret, dict) and 'message' in json_ret:
                raise RemoteError(json_ret['message'])

            raise RemoteError(
                f'ICONOMI api request for {response.url} '
                f'failed with HTTP status code {response.status_code}',
            )

        return json_ret

    def validate_api_key(self) -> tuple[bool, str]:
        """
        Validates that the ICONOMI API key is good for usage in rotki
        """

        try:
            self._api_query('get', 'user/balance')
        except RemoteError:
            return False, 'Provided API Key is invalid'
        else:
            return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        assets_balance: dict[AssetWithOracles, Balance] = {}
        main_currency = CachedSettings().main_currency
        try:
            resp_info = self._api_query('get', 'user/balance')
        except RemoteError as e:
            msg = (
                'ICONOMI API request failed. Could not reach ICONOMI due '
                f'to {e}'
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
                    amount = deserialize_fval(balance_info['balance'])
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        f'Skipping iconomi balance entry {balance_info} due to {msg}',
                    )
                    continue

                try:
                    price = Inquirer.find_price(from_asset=asset, to_asset=main_currency)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing Iconomi balance entry due to inability to '
                        f'query price: {e!s}. Skipping balance entry',
                    )
                    continue

                assets_balance[asset] = Balance(
                    amount=amount,
                    value=amount * price,
                )
            except UnsupportedAsset:
                self.msg_aggregator.add_warning(
                    f'Found unsupported ICONOMI asset {ticker}. '
                    f' Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue

        for balance_info in resp_info['daaList']:
            ticker = balance_info['ticker']

            if ticker == 'AUSTS':
                # The AUSTS strategy is 'ICONOMI Earn'. We know that this strategy holds its
                # value in Anchor UST (AUST). That's why we report the user balance for this
                # strategy as usd_value / AUST price.
                try:
                    aust_usd_price = Inquirer.find_usd_price(asset=A_AUST)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing ICONOMI balance entry due to inability to '
                        f'query USD price: {e!s}. Skipping balance entry',
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

                amount = usd_value / aust_usd_price
                try:
                    price = Inquirer.find_price(from_asset=self.aust, to_asset=main_currency)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing Iconomi balance entry due to inability to '
                        f'query price: {e!s}. Skipping balance entry',
                    )
                    continue

                assets_balance[self.aust] = Balance(
                    amount=amount,
                    value=amount * price,
                )
            else:
                self.msg_aggregator.add_warning(
                    f'Found unsupported ICONOMI strategy {ticker}. '
                    f' Ignoring its balance query.',
                )

        return assets_balance, ''

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple['Sequence[HistoryBaseEntry]', Timestamp]:
        page, all_transactions, events = 0, [], []
        while True:
            resp = self._api_query('get', 'user/activity', {'pageNumber': str(page)})
            if len(resp['transactions']) == 0:
                break

            all_transactions.extend(resp['transactions'])
            page += 1

        log.debug('ICONOMI trade history query', results_num=len(all_transactions))
        for tx in all_transactions:
            try:
                if (
                    tx['type'] not in {'buy_asset', 'sell_asset'} or
                    not (start_ts <= (timestamp := tx['timestamp']) <= end_ts)
                ):
                    continue

                events.extend(create_swap_events(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=self.location,
                    spend=AssetAmount(
                        asset=asset_from_iconomi(tx['source_ticker']),
                        amount=deserialize_fval(tx['source_amount']),
                    ),
                    receive=AssetAmount(
                        asset=asset_from_iconomi(tx['target_ticker']),
                        amount=deserialize_fval(tx['target_amount']),
                    ),
                    fee=AssetAmount(
                        asset=asset_from_iconomi(tx['fee_ticker']),
                        amount=deserialize_fval_or_zero(tx['fee_amount']),
                    ),
                    location_label=self.name,
                    group_identifier=create_group_identifier_from_unique_id(
                        location=self.location,
                        unique_id=str(tx['transactionId']),
                    ),
                ))
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='transaction',
                )
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing an iconomi transaction. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(msg='Error processing an iconomi transaction', error=msg, trade=tx)

        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for iconomi
