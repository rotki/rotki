import json
import logging
from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Literal, overload
from urllib.parse import urlencode

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.converters import asset_from_bitpanda
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BEST
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import (
    ExchangeQueryBalances,
    ExchangeWithoutApiSecret,
)
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
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_movement_event_type,
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_int_from_str,
)
from rotkehlchen.types import ApiKey, AssetAmount, ExchangeAuthCredentials, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict
from rotkehlchen.utils.concurrency import sleep

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_PAGE_SIZE = 100


class Bitpanda(ExchangeWithoutApiSecret):

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__(
            name=name,
            location=Location.BITPANDA,
            api_key=api_key,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.uri = 'https://api.bitpanda.com/v1'
        self.session.headers.update({'X-API-KEY': self.api_key})
        self.cryptocoin_map: dict[str, AssetWithOracles] = {}
        # AssetWithOracles instead of FiatAsset to comply with cryptocoin_map
        self.fiat_map: dict[str, AssetWithOracles] = {}

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        try:
            wallets, _, _ = self._api_query('wallets')
            fiat_wallets, _, _ = self._api_query('fiatwallets')
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query Bitpanda wallets at first connection. {e!s}',
            )
            return

        wallets_len = len(wallets)
        for idx, entry in enumerate(wallets + fiat_wallets):
            if idx < wallets_len:
                id_key = 'cryptocoin_id'
                symbol_key = 'cryptocoin_symbol'
                mapping = self.cryptocoin_map
            else:
                id_key = 'fiat_id'
                symbol_key = 'fiat_symbol'
                mapping = self.fiat_map

            try:
                coin_id = entry['attributes'][id_key]
                asset = asset_from_bitpanda(entry['attributes'][symbol_key])
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='first connection, so not adding asset to mapping',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing Bitpanda wallets query. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing bitpanda wallet entry at first connection',
                    entry=entry,
                    error=msg,
                )
                continue

            mapping[coin_id] = asset

        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'X-API-KEY': self.api_key})

        return changed

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bitpanda API key is good for usage in rotki"""
        try:
            self._api_query('wallets')
        except RemoteError as e:
            return False, f'Error validating Bitpanda API Key due to {e!s}'
        return True, ''

    def _deserialize_wallettx(
            self,
            entry: dict[str, Any],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Deserializes a bitpanda fiatwallets/transactions or wallets/transactions
        entry to a deposit/withdrawal

        Returns None and logs error if there is a problem or simply None if
        it's not a type of entry we are interested in
        """
        try:
            transaction_type = entry['type']
            if (
                transaction_type not in {'fiat_wallet_transaction', 'wallet_transaction'} or
                entry['attributes']['status'] != 'finished'
            ):
                return []
            time = Timestamp(deserialize_int_from_str(
                symbol=entry['attributes']['time']['unix'],
                location='bitpanda wallet transaction',
            ))
            if time < from_ts or time > to_ts:
                # should we also stop querying from calling method?
                # Probably yes but docs don't mention anything about results
                # being ordered by time so let's be conservative
                return []

            try:
                event_type = deserialize_asset_movement_event_type(entry['attributes']['type'])
            except DeserializationError:
                return []  # not a deposit/withdrawal

            if transaction_type == 'fiat_wallet_transaction':
                asset_id = entry['attributes']['fiat_id']
                asset = self.fiat_map.get(asset_id)
            else:
                asset_id = entry['attributes']['cryptocoin_id']
                asset = self.cryptocoin_map.get(asset_id)
            if asset is None:
                self.msg_aggregator.add_error(
                    f'While deserializing Bitpanda fiat transaction, could not find '
                    f'bitpanda asset with id {asset_id} in the mapping',
                )
                return []
            amount = deserialize_fval(entry['attributes']['amount'])
            fee = deserialize_fval_or_zero(entry['attributes']['fee'])
            tx_id = entry['id']

            transaction_id = entry['attributes'].get('tx_id')
            address = entry['attributes'].get('recipient')
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key {msg} for wallet transaction entry'

            self.msg_aggregator.add_error(f'Error processing bitpanda wallet transaction entry due to {msg}')  # noqa: E501
            log.error(
                'Error processing bitpanda wallet transaction entry',
                error=msg,
                entry=entry,
            )
            return []

        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=ts_sec_to_ms(time),
            asset=asset,
            amount=amount,
            fee=AssetAmount(asset=asset, amount=fee),
            unique_id=f'{tx_id}{transaction_id}',  # Use both here as tx_id is not always unique (at least in the test data)  # noqa: E501
            extra_data=maybe_set_transaction_extra_data(
                address=address,
                transaction_id=transaction_id,
            ),
        )

    def _deserialize_trade(
            self,
            entry: dict[str, Any],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> list[SwapEvent]:
        """Deserializes a bitpanda trades result entry to a list of SwapEvents.

        Returns an empty list and logs an error if there is a problem or simply returns an
        empty list if it's not a type of trade we are interested in.
        """
        try:
            if entry['type'] != 'trade' or entry['attributes']['status'] != 'finished':
                return []
            time = Timestamp(deserialize_int_from_str(
                symbol=entry['attributes']['time']['unix'],
                location='bitpanda trade',
            ))
            if time < from_ts or time > to_ts:
                # should we also stop querying from calling method?
                # Probably yes but docs don't mention anything about results
                # being ordered by time so let's be conservative
                return []

            cryptocoin_id = entry['attributes']['cryptocoin_id']
            crypto_asset = self.cryptocoin_map.get(cryptocoin_id)
            if crypto_asset is None:
                self.msg_aggregator.add_error(
                    f'While deserializing a trade, could not find bitpanda cryptocoin '
                    f'with id {cryptocoin_id} in the mapping. Skipping trade.',
                )
                return []

            fiat_id = entry['attributes']['fiat_id']
            fiat_asset = self.fiat_map.get(fiat_id)
            if fiat_asset is None:
                self.msg_aggregator.add_error(
                    f'While deserializing a trade, could not find bitpanda fiat '
                    f'with id {fiat_id} in the mapping. Skipping trade.',
                )
                return []

            fee = ZERO
            if entry['attributes']['bfc_used'] is True:
                fee = deserialize_fval_or_zero(
                    entry['attributes']['best_fee_collection']['attributes']['wallet_transaction']['attributes']['fee'],
                )

            spend, receive = get_swap_spend_receive(
                is_buy=deserialize_trade_type_is_buy(entry['attributes']['type']),
                base_asset=crypto_asset,
                quote_asset=fiat_asset,
                amount=deserialize_fval(entry['attributes']['amount_cryptocoin']),
                rate=deserialize_price(entry['attributes']['price']),
            )
            return create_swap_events(
                timestamp=ts_sec_to_ms(time),
                location=self.location,
                spend=spend,
                receive=receive,
                fee=AssetAmount(asset=A_BEST, amount=fee),
                location_label=self.name,
                event_identifier=create_event_identifier_from_unique_id(
                    location=self.location,
                    unique_id=str(entry['id']),
                ),
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key {msg} for trade entry'

            self.msg_aggregator.add_error(f'Error processing bitpanda trade due to {msg}')
            log.error(
                'Error processing bitpanda trade entry',
                error=msg,
                entry=entry,
            )
            return []

    @overload
    def _api_query(
            self,
            endpoint: Literal[
                'wallets',
                'fiatwallets',
                'trades',
                'fiatwallets/transactions',
                'wallets/transactions',
            ],
            options: dict[str, Any] | None = None,
    ) -> tuple[list[Any], dict[str, Any] | None, dict[str, Any] | None]:
        ...

    @overload
    def _api_query(
            self,
            endpoint: Literal['asset-wallets'],
            options: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        ...

    def _api_query(
            self,
            endpoint: str,
            options: dict[str, Any] | None = None,
    ) -> tuple[list[Any] | dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        """Performs a bitpanda API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Returns a tuple of:
        - The result data
        - Optional meta dict containing total_count, page and page_size
        - Optional links dict containing next, last and self links

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        """
        request_url = f'{self.uri}/{endpoint}'
        retries_left = CachedSettings().get_query_retry_limit()
        timeout = CachedSettings().get_timeout_tuple()
        if options is not None:
            request_url += '?' + urlencode(options)
        while retries_left > 0:
            log.debug(
                'Bitpanda API query',
                request_url=request_url,
                options=options,
            )
            try:
                response = self.session.get(request_url, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Bitpanda API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                backoff_in_seconds = int(20 / retries_left)
                retries_left -= 1
                log.debug(
                    f'Got a 429 from Bitpanda query of {request_url}. Will backoff '
                    f'for {backoff_in_seconds} seconds. {retries_left} retries left',
                )
                sleep(backoff_in_seconds)
                continue

            if response.status_code != HTTPStatus.OK:
                raise RemoteError(
                    f'Bitpanda API request failed with response: {response.text} '
                    f'and status code: {response.status_code}',
                )

            # we got it, so break
            break

        else:  # retries left are zero
            raise RemoteError(f'Ran out of retries for Bitpanda query of {request_url}')

        try:
            decoded_json = jsonloads_dict(response.text)
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(f'Invalid JSON {response.text} in Bitpanda response. {e}') from e

        if 'data'not in decoded_json:
            raise RemoteError(
                f'Invalid JSON {response.text} in Bitpanda response. Expected "data" key',
            )

        log.debug(f'Got Bitpanda response: {decoded_json}')
        return decoded_json['data'], decoded_json.get('meta'), decoded_json.get('links')

    def _query_endpoint_until_end(
            self,
            endpoint: Literal['trades', 'fiatwallets/transactions', 'wallets/transactions'],
            from_ts: Timestamp | None,
            to_ts: Timestamp | None,
            options: dict[str, Any] | None = None,
    ) -> list['HistoryBaseEntry']:
        """Query a paginated endpoint until all pages are read

        May raise RemoteError
        """
        from_timestamp = from_ts if from_ts is not None else Timestamp(0)
        to_timestamp = to_ts if to_ts is not None else ts_now()
        given_options = options.copy() if options else {}
        page = 1
        count_so_far = 0
        result: list[HistoryBaseEntry] = []
        deserialize_fn = self._deserialize_trade if endpoint == 'trades' else self._deserialize_wallettx  # noqa: E501

        while True:
            given_options['page_size'] = MAX_PAGE_SIZE
            given_options['page'] = page
            data, meta, _ = self._api_query(
                endpoint=endpoint,
                options=given_options,
            )
            for entry in data:
                result.extend(deserialize_fn(entry, from_timestamp, to_timestamp))

            count_so_far += len(data)
            if meta is None or meta.get('total_count') is None:
                raise RemoteError(
                    f'A bitpanda paginated query for {endpoint} did '
                    f'not contain meta["total_count"]',
                )
            if count_so_far >= meta['total_count']:
                break

            page += 1

        return result

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            wallets, _, _ = self._api_query('wallets')
            fiat_wallets, _, _ = self._api_query('fiatwallets')
        except RemoteError as e:
            msg = f'Failed to query Bitpanda balances. {e!s}'
            return None, msg

        assets_balance: defaultdict[AssetWithOracles, Balance] = defaultdict(Balance)
        wallets_len = len(wallets)
        for idx, entry in enumerate(wallets + fiat_wallets):

            if idx < wallets_len:
                symbol_key = 'cryptocoin_symbol'
            else:
                symbol_key = 'fiat_symbol'

            try:
                amount = deserialize_fval(entry['attributes']['balance'])
                asset = asset_from_bitpanda(entry['attributes'][symbol_key])
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing Bitpanda balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing bitpanda balance',
                    entry=entry,
                    error=msg,
                )
                continue

            if amount == ZERO:
                continue

            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Bitpanda balance entry due to inability to '
                    f'query USD price: {e!s}. Skipping balance entry',
                )
                continue
            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance), ''

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        self.first_connection()
        # Should probably also query wallets/transactions for crypto deposits/withdrawals
        # but it does not seem as if they contain them
        events = self._query_endpoint_until_end(
            endpoint='fiatwallets/transactions',
            from_ts=start_ts,
            to_ts=end_ts,
        )
        events.extend(self._query_endpoint_until_end(
            endpoint='wallets/transactions',
            from_ts=start_ts,
            to_ts=end_ts,
        ))
        events.extend(self._query_endpoint_until_end(
            endpoint='trades',
            from_ts=start_ts,
            to_ts=end_ts,
        ))
        return events, end_ts

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for Bitpanda
