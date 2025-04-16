import base64
import datetime
import hashlib
import hmac
import logging
from collections import defaultdict
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode, urljoin

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_okx
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    deserialize_trade_type_is_buy,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_fval_or_zero
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Fee,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OkxEndpoint(Enum):
    CURRENCIES = '/api/v5/asset/currencies'
    TRADING_BALANCE = '/api/v5/account/balance'
    FUNDING_BALANCE = '/api/v5/asset/balances'
    TRADES = '/api/v5/trade/orders-history-archive'
    DEPOSITS = '/api/v5/asset/deposit-history'
    WITHDRAWALS = '/api/v5/asset/withdrawal-history'


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
            msg_aggregator=msg_aggregator,
        )
        self.passphrase = passphrase
        self.base_uri = 'https://www.okx.com/'
        self.session.headers.update({
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
        })

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'OK-ACCESS-KEY': self.api_key})
        if credentials.passphrase is not None:
            self.session.headers.update({'OK-ACCESS-PASSPHRASE': credentials.passphrase})
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
            endpoint: OkxEndpoint,
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
        if endpoint in {OkxEndpoint.TRADES, OkxEndpoint.DEPOSITS, OkxEndpoint.WITHDRAWALS}:
            # supports pagination
            params.update({
                'limit': options.get('limit', ''),
                'after': options.get('after', ''),
            })

        if endpoint == OkxEndpoint.TRADES:
            params.update({
                'instType': 'SPOT',
                'state': 'filled',
            })
            if options.get('start_ts'):
                params['begin'] = str(ts_sec_to_ms(Timestamp(int(options['start_ts']))))
            if options.get('end_ts'):
                params['end'] = str(ts_sec_to_ms(Timestamp(int(options['end_ts']))))

        path = endpoint.value
        if len(params) != 0:
            path += f'?{urlencode(params)}'

        datestr = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')  # noqa: E501
        signature = self._generate_signature(datestr, method, path, '')
        self.session.headers.update({
            'OK-ACCESS-TIMESTAMP': datestr,
            'OK-ACCESS-SIGN': signature,
        })
        url = urljoin(self.base_uri, path)

        log.debug(f'Querying OKX {url} with {method=}')
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
            endpoint: OkxEndpoint,
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
            endpoint: OkxEndpoint,
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
        response = self._api_query(endpoint=OkxEndpoint.TRADING_BALANCE)
        if response.get('code') != '0':
            return False, 'Error validating API credentials'
        return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance
        https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance

        May raise
        - RemoteError if the OKX API or price oracle returns an unexpected response
        """
        currencies_data: list[dict] = []
        data = self._api_query_list(endpoint=OkxEndpoint.TRADING_BALANCE)
        if not (len(data) == 1 and isinstance(data[0], dict)):
            raise RemoteError(
                f'{self.name} trading balance response does not contain dict data[0]',
            )
        try:
            currencies_data.extend(data[0]['details'])
        except KeyError as e:
            msg = f'Missing key: {e!s}'
            raise RemoteError(
                f'{self.name} trading balance API request failed due to unexpected response {msg}',
            ) from e

        currencies_data.extend(self._api_query_list(endpoint=OkxEndpoint.FUNDING_BALANCE))

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        for currency_data in currencies_data:
            try:
                asset = asset_from_okx(okx_name=currency_data['ccy'])
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} balance with unsupported asset '
                    f'{e.identifier}. Ignoring it.',
                )
                continue

            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} {asset.name} balance result due to inability '
                    f'to query USD price: {e!s}. Skipping balance result.',
                )
                continue

            try:
                amount = deserialize_fval(currency_data['availBal']) + deserialize_fval(currency_data['frozenBal'])  # noqa: E501
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

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for okx

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        """
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-deposit-history
        https://www.okx.com/docs-v5/en/#rest-api-funding-get-withdrawal-history
        https://www.okx.com/docs-v5/en/#rest-api-trade-get-order-history-last-3-months

        May raise
        - RemoteError from _api_query_list_paginated
        """
        deposits = self._api_query_list_paginated(
            endpoint=OkxEndpoint.DEPOSITS,
            pagination_key='ts',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        withdrawals = self._api_query_list_paginated(
            endpoint=OkxEndpoint.WITHDRAWALS,
            pagination_key='ordId',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )
        trades = self._api_query_list_paginated(
            endpoint=OkxEndpoint.TRADES,
            pagination_key='ordId',
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
        )

        events: list[AssetMovement | SwapEvent] = []
        for raw_movement in deposits:
            events.extend(self.asset_movement_from_okx(
                raw_movement=raw_movement,
                event_type=HistoryEventType.DEPOSIT,
            ))
        for raw_movement in withdrawals:
            events.extend(self.asset_movement_from_okx(
                raw_movement=raw_movement,
                event_type=HistoryEventType.WITHDRAWAL,
            ))
        for raw_trade in trades:
            events.extend(self.swap_events_from_okx(raw_trade))

        return events, end_ts

    def swap_events_from_okx(self, raw_trade: dict[str, Any]) -> list[SwapEvent]:
        """Converts a raw trade from OKX into SwapEvents.
        If there is an error an empty list is returned and error is logged.
        """
        try:
            timestamp = TimestampMS(int(raw_trade['cTime']))
            try:
                base_asset_str, quote_asset_str = raw_trade['instId'].split('-')
            except ValueError as e:
                raise DeserializationError(
                    f'Expected pair {raw_trade["instId"]} to contain a "-"',
                ) from e
            spend, receive = get_swap_spend_receive(
                is_buy=deserialize_trade_type_is_buy(raw_trade['side']),
                base_asset=asset_from_okx(base_asset_str),
                quote_asset=asset_from_okx(quote_asset_str),
                amount=deserialize_fval(raw_trade['accFillSz']),
                rate=deserialize_price(raw_trade['avgPx']),
            )
            fee_amount = deserialize_fval_or_zero(raw_trade['fee'])
            # fee charged by the platform is represented by a negative number
            if fee_amount < ZERO:
                fee_amount = Fee(-1 * fee_amount)
            fee_asset = asset_from_okx(raw_trade['feeCcy'])
            unique_id = raw_trade['ordId']
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='trade',
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
            return create_swap_events(
                timestamp=timestamp,
                location=self.location,
                spend=spend,
                receive=receive,
                fee=AssetAmount(asset=fee_asset, amount=fee_amount),
                location_label=self.name,
                unique_id=unique_id,
            )

        return []  # this is the error case

    def asset_movement_from_okx(
            self,
            raw_movement: dict[str, Any],
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> list[AssetMovement]:
        """
        Converts a raw asset movement from OKX into an AssetMovement object.
        If there is an error `None` is returned and error is logged.
        """
        try:
            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_type=event_type,
                timestamp=TimestampMS(int(raw_movement['ts'])),
                asset=(asset := asset_from_okx(raw_movement['ccy'])),
                amount=deserialize_fval(raw_movement['amt']),
                fee=AssetAmount(
                    asset=asset,
                    amount=deserialize_fval_or_zero(raw_movement['fee']),
                ) if event_type is HistoryEventType.WITHDRAWAL else None,
                unique_id=(tx_hash := raw_movement['txId']),
                extra_data=maybe_set_transaction_extra_data(
                    address=deserialize_asset_movement_address(raw_movement, 'to', asset),
                    transaction_id=tx_hash,
                ),
            )
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='deposit/withdrawal',
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

        return []
