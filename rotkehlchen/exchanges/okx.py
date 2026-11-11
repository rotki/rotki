import datetime
import logging
from collections import defaultdict
from enum import Enum
from functools import partial
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final, Literal
from urllib.parse import urlencode, urljoin

import requests

from rotkehlchen.api.websockets.typedefs import UserMessageRecord
from rotkehlchen.assets.converters import asset_from_okx
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.constants import OKX_LOCATION_KEY
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import (
    RemoteError,
    cause_for_status,
    cause_for_undecodable_body,
    credential_check_cause_of,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.exchange import (
    ApiKeyCheck,
    ExchangeInterface,
    ExchangeQueryBalances,
    ExchangeWithExtras,
    HistoryEventQueue,
)
from rotkehlchen.exchanges.utils import SignatureGeneratorMixin, deserialize_asset_movement_address
from rotkehlchen.fval import FVal
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
from rotkehlchen.history.events.structures.types import HistoryEventSubType
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.locations.constants import (
    LOCATION_OKX,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_fval_or_zero
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import BadData
from rotkehlchen.utils.misc import ts_sec_to_ms
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

OKX_SUCCESS_CODE: Final = '0'
# earningType of an On-chain Earn order's earning that is estimated and not settled yet
ESTIMATED_EARNING_TYPE: Final = '0'


class OkxEndpoint(Enum):
    CURRENCIES = '/api/v5/asset/currencies'
    TRADING_BALANCE = '/api/v5/account/balance'
    FUNDING_BALANCE = '/api/v5/asset/balances'
    SIMPLE_EARN_BALANCE = '/api/v5/finance/savings/balance'
    ONCHAIN_EARN_ORDERS = '/api/v5/finance/staking-defi/orders-active'
    TRADES = '/api/v5/trade/orders-history-archive'
    DEPOSITS = '/api/v5/asset/deposit-history'
    WITHDRAWALS = '/api/v5/asset/withdrawal-history'


class OkxLocation(SerializableEnumNameMixin):
    GLOBAL = 'www'
    EEA = 'my'
    US = 'app'


class Okx(ExchangeInterface, ExchangeWithExtras, SignatureGeneratorMixin):
    """
    OKX exchange API docs: https://www.okx.com/docs-v5
    """

    # Maximum results returned by an OKX API request
    MAX_RESULTS: Final = 100

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            passphrase: str,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
            okx_location: OkxLocation = OkxLocation.GLOBAL,
    ):
        super().__init__(
            name=name,
            location=LOCATION_OKX,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.passphrase = passphrase
        self.okx_location = okx_location
        self.base_uri = f'https://{okx_location.value}.okx.com/'
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

    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        okx_location = extras.get(OKX_LOCATION_KEY)
        if okx_location is not None:
            self.okx_location = okx_location
            self.base_uri = f'https://{okx_location.value}.okx.com/'

        return True, ''

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
        return self.generate_hmac_b64_signature(prehash)

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
        headers = {
            'OK-ACCESS-TIMESTAMP': datestr,
            'OK-ACCESS-SIGN': signature,
        }
        url = urljoin(self.base_uri, path)

        log.debug(f'Querying OKX {url} with {method=}')
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=CachedSettings().get_timeout_tuple(),
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(
                f'{self.name} API request failed due to {e!s}',
                cause=FailureCause.NETWORK,
            ) from e
        try:
            json_response = response.json()
        except requests.exceptions.JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
                cause=cause_for_undecodable_body(response.status_code),
            ) from e

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'{self.name} API request at {url} responded with error '
                f'status code: {response.status_code} and text: {response.text}',
                cause=cause_for_status(response.status_code),
            )

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
        if response.get('code', OKX_SUCCESS_CODE) != OKX_SUCCESS_CODE:
            raise RemoteError(
                f'{self.name} API request failed: {response}',
                cause=FailureCause.REMOTE_REJECTED,
            )

        data = response.get('data')
        if data is None or not isinstance(data, list):
            raise RemoteError(
                f'{self.name} json response does not contain list `data`: {response}',
                cause=FailureCause.BAD_DATA,
            )
        return data

    def _api_query_list_paginated(
            self,
            endpoint: OkxEndpoint,
            pagination_key: str,
            deserialization_method: Callable[
                [dict[str, Any]],
                list[AssetMovement] | list[SwapEvent],
            ],
            options: dict | None = None,
            event_queue: HistoryEventQueue | None = None,
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
            if event_queue is None:
                all_items.extend(data)
            else:
                page_events: list[AssetMovement | SwapEvent] = []
                for raw_event in data:
                    page_events.extend(deserialization_method(raw_event))
                event_queue.flush(page_events)

            if len(data) < self.MAX_RESULTS:
                break

            earliest_item = data[-1]
            options.update({'after': earliest_item[pagination_key]})

        return all_items

    def validate_api_key(self) -> ApiKeyCheck:
        try:
            response = self._api_query(endpoint=OkxEndpoint.TRADING_BALANCE)
        except RemoteError as e:
            return ApiKeyCheck(False, str(e), credential_check_cause_of(e))

        if response.get('code') != OKX_SUCCESS_CODE:
            return ApiKeyCheck(False, 'Error validating API credentials', FailureCause.AUTH)
        return ApiKeyCheck(True)

    def _add_balance_amount(
            self,
            amounts: defaultdict[AssetWithOracles, FVal],
            balance_entry: dict[str, Any],
            amount_keys: tuple[str, ...],
    ) -> None:
        """Adds the sum of the `amount_keys` of an OKX balance entry to the amount of its
        currency in `amounts`. An entry that can't be read is reported and skipped."""
        try:
            asset = asset_from_okx(okx_name=balance_entry['ccy'])
            amount = sum(
                (deserialize_fval(balance_entry[key]) for key in amount_keys),
                start=ZERO,
            )
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='balance query',
            )
            return
        except (DeserializationError, KeyError) as e:
            error = f'missing key {e!s}' if isinstance(e, KeyError) else str(e)
            self.add_classified_error(
                f'Error processing {self.name} {balance_entry.get("ccy")} balance result due '
                f'to {error}. Skipping balance result.',
                BadData(record=UserMessageRecord.BALANCE, error=error),
            )
            return

        amounts[asset] += amount

    def _query_earn_balances(self, amounts: defaultdict[AssetWithOracles, FVal]) -> None:
        """Adds the Simple Earn flexible balances and the principal and accrued earnings of the
        active On-chain Earn orders to `amounts`.

        Earn is not offered in every region and to every account, so a failed query is logged
        and skipped instead of failing the whole balance query.

        https://www.okx.com/docs-v5/en/#financial-product-simple-earn-flexible-get-saving-balance
        https://www.okx.com/docs-v5/en/#financial-product-on-chain-earn-get-active-orders
        """
        try:
            savings = self._api_query_list(endpoint=OkxEndpoint.SIMPLE_EARN_BALANCE)
        except RemoteError as e:
            log.warning('Failed to query %s Simple Earn balances due to %s', self.name, e)
        else:
            for entry in savings:
                # amt is the whole balance: the lent loanAmt plus the pendingAmt not lent yet.
                # The earnings are already added to it, so they are not counted on their own.
                self._add_balance_amount(
                    amounts=amounts,
                    balance_entry=entry,
                    amount_keys=('amt',),
                )

        try:
            orders = self._api_query_list(endpoint=OkxEndpoint.ONCHAIN_EARN_ORDERS)
        except RemoteError as e:
            log.warning('Failed to query %s On-chain Earn orders due to %s', self.name, e)
            return

        for order in orders:
            for entry in order.get('investData', []):
                self._add_balance_amount(
                    amounts=amounts,
                    balance_entry=entry,
                    amount_keys=('amt',),
                )
            for entry in order.get('earningData', []):
                # Type 0 is the estimated earning not settled yet. Type 1 is the cumulative
                # earning, which for some products is already paid out to the funding account
                # and would be counted twice.
                if entry.get('earningType') == ESTIMATED_EARNING_TYPE:
                    self._add_balance_amount(
                        amounts=amounts,
                        balance_entry=entry,
                        amount_keys=('earnings',),
                    )

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """
        https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance
        https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance
        """
        try:
            data = self._api_query_list(endpoint=OkxEndpoint.TRADING_BALANCE)
            funding_data = self._api_query_list(endpoint=OkxEndpoint.FUNDING_BALANCE)
        except RemoteError as e:
            msg = str(e)
            log.error('%s Api request failed due to %s', self.name, msg)
            return ExchangeQueryBalances(None, msg, e.cause)

        if not (len(data) == 1 and isinstance(data[0], dict)):
            msg = 'trading balance response does not contain dict data[0]'
            log.error('%s API request failed due to %s', self.name, msg)
            return ExchangeQueryBalances(None, msg, FailureCause.BAD_DATA)

        try:
            trading_data = data[0]['details']
        except KeyError as e:
            msg = f'Missing key: {e!s}'
            log.error('%s API request failed due to %s', self.name, msg)
            return ExchangeQueryBalances(None, msg, FailureCause.BAD_DATA)

        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        for currency_data in trading_data + funding_data:
            self._add_balance_amount(
                amounts=amounts,
                balance_entry=currency_data,
                amount_keys=('availBal', 'frozenBal'),
            )

        self._query_earn_balances(amounts)
        return ExchangeQueryBalances(dict(self.balances_from_amounts(amounts)), '')

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
            force_refresh: bool = False,
            event_queue: HistoryEventQueue | None = None,
    ) -> tuple[Sequence[HistoryBaseEntry], Timestamp]:
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
            deserialization_method=partial(
                self.asset_movement_from_okx,
                event_subtype=HistoryEventSubType.RECEIVE,
            ),
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
            event_queue=event_queue,
        )
        withdrawals = self._api_query_list_paginated(
            endpoint=OkxEndpoint.WITHDRAWALS,
            pagination_key='ts',
            deserialization_method=partial(
                self.asset_movement_from_okx,
                event_subtype=HistoryEventSubType.SPEND,
            ),
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
            event_queue=event_queue,
        )
        trades = self._api_query_list_paginated(
            endpoint=OkxEndpoint.TRADES,
            pagination_key='ordId',
            deserialization_method=self.swap_events_from_okx,
            options={
                'start_ts': start_ts,
                'end_ts': end_ts,
            },
            event_queue=event_queue,
        )

        events: list[AssetMovement | SwapEvent] = []
        for raw_movement in deposits:
            events.extend(self.asset_movement_from_okx(
                raw_movement=raw_movement,
                event_subtype=HistoryEventSubType.RECEIVE,
            ))
        for raw_movement in withdrawals:
            events.extend(self.asset_movement_from_okx(
                raw_movement=raw_movement,
                event_subtype=HistoryEventSubType.SPEND,
            ))
        for raw_trade in trades:
            events.extend(self.swap_events_from_okx(raw_trade))

        return events, end_ts

    def query_online_history_events_into_queue(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
    ) -> Timestamp:
        _, actual_end_ts = self.query_online_history_events(
            start_ts=start_ts,
            end_ts=end_ts,
            event_queue=event_queue,
        )
        return actual_end_ts

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
                fee_amount *= -1
            fee_asset = asset_from_okx(raw_trade['feeCcy'])
            unique_id = raw_trade['ordId']
        except UnknownAsset as e:
            self.send_unknown_asset_message(
                asset_identifier=e.identifier,
                details='trade',
            )
        except (DeserializationError, KeyError) as e:
            self.add_classified_error(
                f'Unexpected data encountered during deserialization of {self.name}'
                'trade. Check logs for details and open a bug report.',
                BadData(record=UserMessageRecord.TRADE, error=str(e)),
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
                group_identifier=create_group_identifier_from_unique_id(
                    location=self.location,
                    unique_id=unique_id,
                ),
            )

        return []  # this is the error case

    def asset_movement_from_okx(
            self,
            raw_movement: dict[str, Any],
            event_subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.SPEND],
    ) -> list[AssetMovement]:
        """
        Converts a raw asset movement from OKX into an AssetMovement object.
        If there is an error `None` is returned and error is logged.
        """
        try:
            return create_asset_movement_with_fee(
                location=self.location,
                location_label=self.name,
                event_subtype=event_subtype,
                timestamp=TimestampMS(int(raw_movement['ts'])),
                asset=(asset := asset_from_okx(raw_movement['ccy'])),
                amount=deserialize_fval(raw_movement['amt']),
                fee=AssetAmount(
                    asset=asset,
                    amount=deserialize_fval_or_zero(raw_movement['fee']),
                ) if event_subtype == HistoryEventSubType.SPEND else None,
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
        except (DeserializationError, KeyError) as e:
            self.add_classified_error(
                f'Unexpected data encountered during deserialization of {self.name} '
                'asset movement. Check logs for details and open a bug report.',
                BadData(record=UserMessageRecord.ASSET_MOVEMENT, error=str(e)),
            )
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            log.error(
                f'Unexpected data encountered during deserialization of {self.name} '
                f'asset_movement {raw_movement}. Error was: {msg}',
            )

        return []
