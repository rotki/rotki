import base64
import datetime
import hashlib
import hmac
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode, urljoin

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_okx
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_fee
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    ExchangeAuthCredentials,
    Fee,
    Location,
    Timestamp,
    TimestampMS,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.base import HistoryEvent
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Okx(ExchangeInterface):
    """
    OKX exchange API docs: https://www.okx.com/docs-v5
    """

    # Maximum results returned by an OKX API request
    MAX_RESULTS = 100

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            passphrase: str,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.OKX,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.passphrase = passphrase
        self.base_uri = 'https://www.okx.com/'
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
        })

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'OK-ACCESS-KEY': self.api_key})
        if credentials.passphrase is not None:
            self.session.headers.update({'OK-ACCESS-PASSPHRASE': self.passphrase})
        return changed

    def _generate_signature(
            self,
            datestr: str,
            method: Literal['GET', 'PUT', 'PATCH', 'DELETE'],
            path: str,
            body: str,
    ) -> str:
        """
        https://www.okx.com/docs-v5/en/#rest-api-authentication-signature
        """
        prehash = datestr + method + path + body
        signature = hmac.new(self.secret, prehash.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(signature.digest()).decode('utf-8')

    def _api_query(
            self,
            endpoint: Literal['currencies', 'balance', 'trades', 'deposits', 'withdrawals'],
            options: dict | None = None,
    ) -> dict:
        """
        Makes an API query to OKX

        May raise:
        - RemoteError if request fails or returns invalid JSON
        """
        method: Literal['GET', 'PUT', 'PATCH', 'DELETE'] = 'GET'
        options = options.copy() if options else {}

        params = {}
        if endpoint == 'currencies':
            path = '/api/v5/asset/currencies'
        elif endpoint == 'balance':
            path = '/api/v5/account/balance'
        elif endpoint == 'trades':
            path = '/api/v5/trade/orders-history-archive'
            # supports pagination
            params.update({
                'limit': options.get('limit', ''),
                'after': options.get('after', ''),
            })
            params.update({
                'instType': 'SPOT',
                'state': 'filled',
            })
            if options.get('start_ts'):
                params['begin'] = str(ts_sec_to_ms(Timestamp(int(options['start_ts']))))
            if options.get('end_ts'):
                params['end'] = str(ts_sec_to_ms(Timestamp(int(options['end_ts']))))
        elif endpoint == 'deposits':
            path = '/api/v5/asset/deposit-history'
            # supports pagination
            params.update({
                'limit': options.get('limit', ''),
                'after': options.get('after', ''),
            })
        else:
            assert endpoint == 'withdrawals', 'only case left, should be withdrawals'
            path = '/api/v5/asset/withdrawal-history'
            # supports pagination
            params.update({
                'limit': options.get('limit', ''),
                'after': options.get('after', ''),
            })

        if len(params) != 0:
            path += f'?{urlencode(params)}'

        datestr = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')  # noqa: E501
        signature = self._generate_signature(datestr, method, path, '')
        self.session.headers.update({
            'OK-ACCESS-TIMESTAMP': datestr,
            'OK-ACCESS-SIGN': signature,
        })
        url = urljoin(self.base_uri, path)

        try:
            response = self.session.request(method=method, url=url)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'{self.name} API request failed due to {e!s}') from e
        try:
            json_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
            ) from e

        return json_response

    def _api_query_list(
            self,
            endpoint: Literal['currencies', 'balance', 'trades', 'deposits', 'withdrawals'],
            options: dict | None = None,
    ) -> list:
        """
        Makes an API query and parses the response into a list

        May raise
        - RemoteError if the API returns an unexpected response
        """
        response = self._api_query(endpoint=endpoint, options=options)
        data = response.get('data')
        if data is None or not isinstance(data, list):
            raise RemoteError(
                f'{self.name} json response does not contain list `data`: {response}',
            )
        return data

    def _api_query_list_paginated(
            self,
            endpoint: Literal['currencies', 'balance', 'trades', 'deposits', 'withdrawals'],
            pagination_key: str,
            options: dict | None = None,
    ) -> list:
        """
        Makes subsequent API queries until response list length is less than MAX_RESULTS.
        Pagination is handled by setting `pagination_key` value in the `after` query parameter.
        This returns items with `pagination_key` value less than the passed value

        May raise
        - RemoteError if the API returns an unexpected response
        """
        options = options.copy() if options else {}
        all_items = []

        while True:
            data = self._api_query_list(endpoint=endpoint, options=options)
            all_items.extend(data)
            if len(data) < self.MAX_RESULTS:
                break

            earliest_item = data[-1]
            options.update({'after': earliest_item[pagination_key]})

        return all_items

    def validate_api_key(self) -> tuple[bool, str]:
        response = self._api_query(endpoint='balance')
        if response.get('code') != '0':
            return False, 'Error validating API credentials'
        return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        https://www.okx.com/docs-v5/en/#rest-api-account-get-balance

        May raise
        - RemoteError if the OKX API or price oracle returns an unexpected response
        """
        data = self._api_query_list(endpoint='balance')
        if not (len(data) == 1 and isinstance(data[0], dict)):
            raise RemoteError(
                f'{self.name} balance response does not contain dict data[0]',
            )
        try:
            currencies_data = data[0]['details']
        except KeyError as e:
            msg = f'Missing key: {e!s}'
            raise RemoteError(
                f'{self.name} balance API request failed due to unexpected response {msg}',
            ) from e

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for currency_data in currencies_data:
            try:
                asset = asset_from_okx(okx_name=currency_data['ccy'])
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} balance with unknown asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} balance with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to query USD price: {e!s}. Skipping balance result.',
                )
                continue

            try:
                amount = deserialize_asset_amount(currency_data['availBal'])
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to deserialize asset amount due to {e!s}. Skipping balance result.',
                )
                continue

            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance), ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
        """
        https://www.okx.com/docs-v5/en/#rest-api-trade-get-order-history-last-3-months

        May raise
        - RemoteError from _api_query_list_paginated
        """
        raw_trades = self._api_query_list_paginated(
            endpoint='trades',
            pagination_key='ordId',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )

        trades: list[Trade] = []
        for raw_trade in raw_trades:
            trade = self.trade_from_okx(raw_trade)
            if trade is not None:
                trades.append(trade)

        return trades, (start_ts, end_ts)

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for okx

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-deposit-history
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-withdrawal-history

        May raise
        - RemoteError from _api_query_list_paginated
        """
        deposits = self._api_query_list_paginated(
            endpoint='deposits',
            pagination_key='ts',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        withdrawals = self._api_query_list_paginated(
            endpoint='withdrawals',
            pagination_key='ordId',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )

        movements: list[AssetMovement] = []
        for raw_movement in deposits:
            movement = self.asset_movement_from_okx(
                raw_movement=raw_movement,
                category=AssetMovementCategory.DEPOSIT,
            )
            if movement is not None:
                movements.append(movement)
        for raw_movement in withdrawals:
            movement = self.asset_movement_from_okx(
                raw_movement=raw_movement,
                category=AssetMovementCategory.WITHDRAWAL,
            )
            if movement is not None:
                movements.append(movement)

        return movements

    def query_online_income_loss_expense(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list['HistoryEvent']:
        return []  # noop for okx

    def trade_from_okx(self, raw_trade: dict[str, Any]) -> Trade | None:
        """
        Converts a raw trade from OKX into a Trade object.
        If there is an error `None` is returned and error is logged.
        """
        try:
            timestamp = ts_ms_to_sec(TimestampMS(int(raw_trade['cTime'])))
            try:
                base_asset_str, quote_asset_str = raw_trade['instId'].split('-')
            except ValueError as e:
                raise DeserializationError(
                    f'Expected pair {raw_trade["instId"]} to contain a "-"',
                ) from e
            base_asset = asset_from_okx(base_asset_str)
            quote_asset = asset_from_okx(quote_asset_str)
            trade_type = TradeType.deserialize(raw_trade['side'])
            amount = deserialize_asset_amount(raw_trade['accFillSz'])
            rate = deserialize_price(raw_trade['avgPx'])
            fee_amount = deserialize_fee(raw_trade['fee'])
            # fee charged by the platform is represented by a negative number
            if fee_amount < 0:
                fee_amount = Fee(-1 * fee_amount)
            fee_asset = asset_from_okx(raw_trade['feeCcy'])
            link = raw_trade['ordId']
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} trade with unknown asset '
                f'{e.identifier}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} trade with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            self.msg_aggregator.add_error(
                f'Unexpected data encountered during deserialization of {self.name}'
                'trade. Check logs for details and open a bug report.',
            )
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            log.error(
                f'Unexpected data encountered during deserialization of {self.name} '
                f'trade {raw_trade}. Error was: {msg}',
            )
        else:
            return Trade(
                timestamp=timestamp,
                location=Location.OKX,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=amount,
                rate=rate,
                fee=fee_amount,
                fee_currency=fee_asset,
                link=link,
            )

        return None

    def asset_movement_from_okx(
            self,
            raw_movement: dict[str, Any],
            category: AssetMovementCategory,
    ) -> AssetMovement | None:
        """
        Converts a raw asset movement from OKX into an AssetMovement object.
        If there is an error `None` is returned and error is logged.
        """
        asset_movement = None
        try:
            tx_hash = raw_movement['txId']
            timestamp = ts_ms_to_sec(TimestampMS(int(raw_movement['ts'])))
            asset = asset_from_okx(raw_movement['ccy'])
            amount = deserialize_asset_amount(raw_movement['amt'])
            address = deserialize_asset_movement_address(raw_movement, 'to', asset)
            fee = Fee(ZERO)
            if category is AssetMovementCategory.WITHDRAWAL:
                fee = deserialize_fee(raw_movement['fee'])

            asset_movement = AssetMovement(
                location=Location.OKX,
                category=category,
                address=address,
                transaction_id=tx_hash,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                fee=fee,
                link=tx_hash,
            )
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} deposit/withdrawal with unknown asset '
                f'{e.identifier}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {self.name} deposit/withdrawal with unsupported asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            self.msg_aggregator.add_error(
                f'Unexpected data encountered during deserialization of {self.name} '
                'asset movement. Check logs for details and open a bug report.',
            )
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            log.error(
                f'Unexpected data encountered during deserialization of {self.name} '
                f'asset_movement {raw_movement}. Error was: {msg}',
            )

        return asset_movement
