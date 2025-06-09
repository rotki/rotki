import hashlib
import hmac
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Sequence
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Location, MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_movement_event_type,
    deserialize_fval,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Price,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_sec_to_ms
from rotkehlchen.utils.concurrency import sleep

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def independentreserve_asset(symbol: str) -> AssetWithOracles:
    """Returns the asset corresponding to the independentreserve symbol

    May raise:
    - UnsupportedAsset
    - UnknownAsset
    """
    return symbol_to_asset_or_token(GlobalDBHandler.get_assetid_from_exchange_name(
        exchange=Location.INDEPENDENTRESERVE,
        symbol=symbol,
        default=symbol,
    ))


def _asset_movement_from_independentreserve(raw_tx: dict) -> AssetMovement | None:
    """Convert IndependentReserve raw data to an AssetMovement

    https://www.independentreserve.com/products/api#GetTransactions
    May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    - KeyError
    """
    log.debug(f'Processing raw IndependentReserve transaction: {raw_tx}')
    movement_type = deserialize_asset_movement_event_type(raw_tx['Type'])
    asset = independentreserve_asset(raw_tx['CurrencyCode'])
    bitcoin_tx_id = raw_tx.get('BitcoinTransactionId')
    eth_tx_id = raw_tx.get('EthereumTransactionId')
    if asset == A_BTC and bitcoin_tx_id is not None:
        transaction_id = raw_tx['BitcoinTransactionId']
    elif eth_tx_id is not None:
        transaction_id = eth_tx_id
    else:
        transaction_id = None

    comment = raw_tx.get('Comment')
    address = None
    if comment is not None and comment.startswith('Withdrawing to'):
        address = comment.rsplit()[-1]

    raw_amount = raw_tx.get('Credit') if movement_type == HistoryEventType.DEPOSIT else raw_tx.get('Debit')  # noqa: E501

    if raw_amount is None:  # skip
        return None   # Can end up being None for some things like this: 'Comment': 'Initial balance after Bitcoin fork'  # noqa: E501
    amount = deserialize_fval(raw_amount)

    return AssetMovement(
        location=Location.INDEPENDENTRESERVE,
        event_type=movement_type,
        timestamp=ts_sec_to_ms(deserialize_timestamp_from_date(
            date=raw_tx['CreatedTimestampUtc'],
            formatstr='iso8601',
            location='IndependentReserve',
        )),
        asset=asset,
        amount=amount,
        unique_id=raw_tx.get('TransactionGuid'),
        extra_data=maybe_set_transaction_extra_data(
            address=address,
            transaction_id=transaction_id,
        ),
    )


class Independentreserve(ExchangeInterface):
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
            location=Location.INDEPENDENTRESERVE,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://api.independentreserve.com'
        self.session.headers.update({'Content-Type': 'application/json'})
        self.account_guids: list | None = None

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'x-api-key': credentials.api_key})
        return changed

    def _api_query(
            self,
            verb: Literal['get', 'post'],
            method_type: Literal['Public', 'Private'],
            path: str,
            options: dict | None = None,
    ) -> dict:
        """An IndependentrReserve query

        May raise RemoteError
        """
        url = f'{self.uri}/{method_type}/{path}'
        timeout = CachedSettings().get_timeout_tuple()
        tries = CachedSettings().get_query_retry_limit()
        while True:
            data = None
            log.debug(
                'IndependentReserve API Query',
                verb=verb,
                url=url,
                options=options,
            )
            if method_type == 'Private':
                nonce = int(time.time() * 1000)
                call_options = OrderedDict(options.copy()) if options else OrderedDict()
                call_options.update({
                    'nonce': nonce,
                    'apiKey': self.api_key,
                })
                # Make sure dict starts with apiKey, nonce
                call_options.move_to_end('nonce', last=False)
                call_options.move_to_end('apiKey', last=False)
                keys = [url] + [f'{k}={v}' for k, v in call_options.items()]
                message = ','.join(keys)
                signature = hmac.new(
                    self.secret,
                    msg=message.encode('utf-8'),
                    digestmod=hashlib.sha256,
                ).hexdigest().upper()
                # Make sure dict starts with apiKey, nonce, signature
                call_options['signature'] = str(signature)
                call_options.move_to_end('signature', last=False)
                call_options.move_to_end('nonce', last=False)
                call_options.move_to_end('apiKey', last=False)
                data = json.dumps(call_options, sort_keys=False)
            try:
                response = self.session.request(
                    method=verb,
                    url=url,
                    data=data,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'IndependentReserve API request failed due to {e!s}') from e

            if response.status_code not in {200, 429}:
                raise RemoteError(
                    f'IndependentReserve api request for {response.url} failed with HTTP status '
                    f'code {response.status_code} and response {response.text}',
                )

            if response.status_code == 429:
                if tries >= 1:
                    backoff_seconds = 10 / tries
                    log.debug(
                        f'Got a 429 from IndependentReserve. Backing off for {backoff_seconds}')
                    sleep(backoff_seconds)
                    tries -= 1
                    continue

                # else
                raise RemoteError(
                    f'IndependentReserve api request for {response.url} failed with HTTP '
                    f'status code {response.status_code} and response {response.text}',
                )

            break  # else all good, we can break off the retry loop

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as e:
            raise RemoteError('IndependentReserve returned invalid JSON response') from e

        return json_ret

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the IndependentReserve API key is good for usage in rotki"""
        try:
            self._api_query(verb='post', method_type='Private', path='GetAccounts')
        except RemoteError as e:
            return False, str(e)
        else:
            return True, ''

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        assets_balance: dict[AssetWithOracles, Balance] = {}
        try:
            response = self._api_query(verb='post', method_type='Private', path='GetAccounts')
        except RemoteError as e:
            msg = f'IndependentReserve request failed. Could not reach the exchange due to {e!s}'
            log.error(msg)
            return None, msg

        log.debug(f'IndependentReserve account response: {response}')
        account_guids = []
        for entry in response:
            try:
                asset = independentreserve_asset(entry['CurrencyCode'])
                usd_price = Inquirer.find_usd_price(asset=asset)
                amount = deserialize_fval(entry['TotalBalance'])
                account_guids.append(entry['AccountGuid'])
            except UnsupportedAsset as e:
                log.error(
                    f'Found unsupported {self.name} asset {e.identifier}. '
                    f'Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except RemoteError as e:  # raised only by find_usd_price
                self.msg_aggregator.add_error(
                    f'Error processing IndependentReserve balance entry due to inability to '
                    f'query USD price: {e!s}. Skipping balance entry',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                return None, f'Error processing IndependentReserve balance entry {entry}. {msg}'

            if amount == ZERO:
                continue

            assets_balance[asset] = Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        self.account_guids = account_guids
        return assets_balance, ''

    def _gather_paginated_data(self, path: str, extra_options: dict | None = None) -> list[dict[str, Any]]:  # noqa: E501
        """May raise KeyError"""
        page = 1
        page_size = 50
        data = []
        while True:
            call_options = extra_options.copy() if extra_options is not None else {}
            call_options.update({'pageIndex': page, 'pageSize': page_size})
            resp = self._api_query(
                verb='post',
                method_type='Private',
                path=path,
                options=call_options,
            )
            data.extend(resp['Data'])
            if len(resp['Data']) < 50:
                break  # get out of the loop

            page += 1  # go to the next page

        return data

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Query IndependentReserve trades and convert them into SwapEvents.
        https://www.independentreserve.com/products/api#GetClosedFilledOrders
        May raise RemoteError.
        """
        try:
            resp_trades = self._gather_paginated_data(path='GetClosedFilledOrders')
        except KeyError as e:
            self.msg_aggregator.add_error(
                f'Error processing independentreserve trades response. '
                f'Missing key: {e!s}.',
            )
            return []

        events = []
        for raw_trade in resp_trades:
            try:
                log.debug(f'Processing raw IndependentReserve trade: {raw_trade}')
                timestamp = deserialize_timestamp_from_date(
                    date=raw_trade['CreatedTimestampUtc'],
                    formatstr='iso8601',
                    location='IndependentReserve',
                )
                if timestamp < start_ts or timestamp > end_ts:
                    continue

                spend, receive = get_swap_spend_receive(
                    is_buy='Bid' in raw_trade['OrderType'],
                    base_asset=(base_asset := independentreserve_asset(raw_trade['PrimaryCurrencyCode'])),  # noqa: E501
                    quote_asset=independentreserve_asset(raw_trade['SecondaryCurrencyCode']),
                    amount=(amount := (FVal(raw_trade['Volume']) - FVal(raw_trade['Outstanding']))),  # noqa: E501
                    rate=Price(FVal(raw_trade['AvgPrice'])),
                )
                events.extend(create_swap_events(
                    timestamp=ts_sec_to_ms(timestamp),
                    location=self.location,
                    spend=spend,
                    receive=receive,
                    fee=AssetAmount(
                        asset=base_asset,
                        amount=FVal(raw_trade['FeePercent']) * amount,
                    ),
                    location_label=self.name,
                    event_identifier=create_event_identifier_from_unique_id(
                        location=self.location,
                        unique_id=str(raw_trade['OrderGuid']),
                    ),
                ))
            except UnsupportedAsset as e:
                log.error(
                    f'Found unsupported {self.name} asset {e.identifier}. '
                    f'Ignoring this trade entry {raw_trade}.',
                )
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='trade',
                )
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing an IndependentReserve trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing an IndependentReserve trade',
                    trade=raw_trade,
                    error=msg,
                )

        return events

    def _query_asset_movements(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list['AssetMovement']:
        if self.account_guids is None:
            self.query_balances()  # do a balance query to populate the account guids
        movements = []
        for guid in self.account_guids:  # type: ignore  # we know its not None
            try:
                resp = self._gather_paginated_data(
                    path='GetTransactions',
                    extra_options={
                        'accountGuid': guid,
                        'fromTimestampUtc': timestamp_to_iso8601(start_ts, utc_as_z=True),
                        'toTimestampUtc': timestamp_to_iso8601(end_ts, utc_as_z=True),
                        # if we filter by tx type in my tests I started getting
                        # this {"Message":"A server error occurred. Please wait a few minutes and try again."}   # noqa: E501
                    },
                )
            except KeyError as e:
                self.msg_aggregator.add_error(
                    f'Error processing IndependentReserve transactions response. '
                    f'Missing key: {e!s}.',
                )
                return []

            for entry in resp:
                entry_type = entry.get('Type')
                if entry_type is None or entry_type not in {'Deposit', 'Withdrawal'}:
                    continue

                try:
                    movement = _asset_movement_from_independentreserve(entry)
                    if movement:
                        movements.append(movement)
                except UnsupportedAsset as e:
                    log.error(
                        f'Found unsupported {self.name} asset {e.identifier}. '
                        f'Ignoring this asset movement entry {entry}.',
                    )
                    continue
                except UnknownAsset as e:
                    self.send_unknown_asset_message(
                        asset_identifier=e.identifier,
                        details='deposit/withdrawal',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        'Failed to deserialize an IndependentReserve deposit/withdrawal. '
                        'Check logs for details. Ignoring it.',
                    )
                    log.error(
                        'Error processing an IndependentReserve deposit/withdrawal.',
                        raw_asset_movement=entry,
                        error=msg,
                    )
                    continue

        return movements

    def query_online_history_events(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        events: list[AssetMovement | SwapEvent] = []
        for query_func in (self._query_asset_movements, self._query_trades):
            events.extend(query_func(start_ts=start_ts, end_ts=end_ts))

        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for independentreserve
