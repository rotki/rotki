import json
import logging
from collections import defaultdict
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    overload,
)
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bitpanda
from rotkehlchen.constants.assets import A_BEST
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, QUERY_RETRY_TIMES
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_int_from_str,
)
from rotkehlchen.types import ApiKey, ApiSecret, Fee, Location, Timestamp, TradeType
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

MAX_PAGE_SIZE = 100


class Bitpanda(ExchangeInterface):  # lgtm[py/missing-call-to-init]

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
            location=Location.BITPANDA,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.uri = 'https://api.bitpanda.com/v1'
        self.session.headers.update({'X-API-KEY': self.api_key})
        self.msg_aggregator = msg_aggregator
        self.cryptocoin_map: Dict[str, AssetWithOracles] = {}
        # AssetWithOracles instead of FiatAsset to comply with cryptocoin_map
        self.fiat_map: Dict[str, AssetWithOracles] = {}

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        try:
            wallets, _, _ = self._api_query('wallets')
            fiat_wallets, _, _ = self._api_query('fiatwallets')
        except RemoteError as e:
            self.msg_aggregator.add_error(
                f'Failed to query Bitpanda wallets at first connection. {str(e)}',
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
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown Bitpanda asset {e.identifier}. '
                    f' Not adding asset to mapping during first connection.',
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

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'X-API-KEY': self.api_key})

        return changed

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Bitpanda API key is good for usage in rotki"""
        try:
            self._api_query('wallets')
        except RemoteError as e:
            return False, f'Error validating Bitpanda API Key due to {str(e)}'
        return True, ''

    def _deserialize_wallettx(
            self,
            entry: Dict[str, Any],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> Optional[AssetMovement]:
        """Deserializes a bitpanda fiatwallets/transactions or wallets/transactions
        entry to a deposit/withdrawal

        Returns None and logs error is there is a problem or simpy None if
        it's not a type of entry we are interested in
        """
        try:
            transaction_type = entry['type']
            if (
                transaction_type not in ('fiat_wallet_transaction', 'wallet_transaction') or
                entry['attributes']['status'] != 'finished'
            ):
                return None
            time = Timestamp(deserialize_int_from_str(
                symbol=entry['attributes']['time']['unix'],
                location='bitpanda wallet transaction',
            ))
            if time < from_ts or time > to_ts:
                # should we also stop querying from calling method?
                # Probably yes but docs don't mention anything about results
                # being ordered by time so let's be conservative
                return None

            try:
                movement_category = deserialize_asset_movement_category(entry['attributes']['type'])  # noqa: E501
            except DeserializationError:
                return None  # not a deposit/withdrawal

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
                return None
            amount = deserialize_asset_amount(entry['attributes']['amount'])
            fee = deserialize_fee(entry['attributes']['fee'])
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
            return None

        return AssetMovement(
            location=Location.BITPANDA,
            category=movement_category,
            address=address,
            transaction_id=transaction_id,
            timestamp=time,
            asset=asset,
            amount=amount,
            fee_asset=asset,
            fee=fee,
            link=tx_id,
        )

    def _deserialize_trade(
            self,
            entry: Dict[str, Any],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> Optional[Trade]:
        """Deserializes a bitpanda trades result entry to a Trade

        Returns None and logs error is there is a problem or simpy None if
        it's not a type of trade we are interested in
        """
        try:
            if entry['type'] != 'trade' or entry['attributes']['status'] != 'finished':
                return None
            time = Timestamp(deserialize_int_from_str(
                symbol=entry['attributes']['time']['unix'],
                location='bitpanda trade',
            ))
            if time < from_ts or time > to_ts:
                # should we also stop querying from calling method?
                # Probably yes but docs don't mention anything about results
                # being ordered by time so let's be conservative
                return None

            cryptocoin_id = entry['attributes']['cryptocoin_id']
            crypto_asset = self.cryptocoin_map.get(cryptocoin_id)
            if crypto_asset is None:
                self.msg_aggregator.add_error(
                    f'While deserializing a trade, could not find bitpanda cryptocoin '
                    f'with id {cryptocoin_id} in the mapping. Skipping trade.',
                )
                return None

            fiat_id = entry['attributes']['fiat_id']
            fiat_asset = self.fiat_map.get(fiat_id)
            if fiat_asset is None:
                self.msg_aggregator.add_error(
                    f'While deserializing a trade, could not find bitpanda fiat '
                    f'with id {fiat_id} in the mapping. Skipping trade.',
                )
                return None

            trade_type = TradeType.deserialize(entry['attributes']['type'])
            if trade_type in (TradeType.BUY, TradeType.SELL):
                # you buy crypto with fiat and sell it for fiat
                base_asset = crypto_asset
                quote_asset = fiat_asset
                amount = deserialize_asset_amount(entry['attributes']['amount_cryptocoin'])
                price = deserialize_price(entry['attributes']['price'])
            else:
                self.msg_aggregator.add_error('Found bitpanda trade with unknown trade type {trade_type}')  # noqa: E501
                return None

            trade_id = entry['id']
            fee = Fee(ZERO)
            fee_asset = A_BEST
            if entry['attributes']['bfc_used'] is True:
                fee = deserialize_fee(
                    entry['attributes']['best_fee_collection']['attributes']['wallet_transaction']['attributes']['fee'],  # noqa: E501
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
            return None

        return Trade(
            timestamp=time,
            location=Location.BITPANDA,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=amount,
            rate=price,
            fee=fee,
            fee_currency=fee_asset,
            link=trade_id,
        )

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal[
                'wallets',
                'fiatwallets',
                'trades',
                'fiatwallets/transactions',
                'wallets/transactions',
            ],
            options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        ...

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['asset-wallets'],
            options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        ...

    def _api_query(
            self,
            endpoint: str,
            options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Union[List[Any], Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:  # noqa: E501
        """Performs a bitpanda API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Returns a tuple of:
        - The result data
        - Optional meta dict containing total_count, page and page_size
        - Optional links dict containing next, last and self links

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        """
        request_url = f'{self.uri}/{endpoint}'
        retries_left = QUERY_RETRY_TIMES
        if options is not None:
            request_url += '?' + urlencode(options)
        while retries_left > 0:
            log.debug(
                'Bitpanda API query',
                request_url=request_url,
                options=options,
            )
            try:
                response = self.session.get(request_url, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Bitpanda API request failed due to {str(e)}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                backoff_in_seconds = int(20 / retries_left)
                retries_left -= 1
                log.debug(
                    f'Got a 429 from Bitpanda query of {request_url}. Will backoff '
                    f'for {backoff_in_seconds} seconds. {retries_left} retries left',
                )
                gevent.sleep(backoff_in_seconds)
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

    @overload
    def _query_endpoint_until_end(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['trades'],
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Trade]:
        ...

    @overload
    def _query_endpoint_until_end(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['fiatwallets/transactions', 'wallets/transactions'],
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            options: Optional[Dict[str, Any]] = None,
    ) -> List[AssetMovement]:
        ...

    def _query_endpoint_until_end(
            self,
            endpoint: Literal['trades', 'fiatwallets/transactions', 'wallets/transactions'],
            from_ts: Optional[Timestamp],
            to_ts: Optional[Timestamp],
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[List[Trade], List[AssetMovement]]:
        """Query a paginated endpoint until all pages are read

        May raise RemoteError
        """
        from_timestamp = from_ts if from_ts is not None else Timestamp(0)
        to_timestamp = to_ts if to_ts is not None else ts_now()
        given_options = options.copy() if options else {}
        page = 1
        count_so_far = 0
        result = []
        deserialize_fn = self._deserialize_trade if endpoint == 'trades' else self._deserialize_wallettx  # noqa: E501

        while True:
            given_options['page_size'] = MAX_PAGE_SIZE
            given_options['page'] = page
            data, meta, _ = self._api_query(
                endpoint=endpoint,
                options=given_options,
            )

            for entry in data:
                decoded_entry = deserialize_fn(entry, from_timestamp, to_timestamp)
                if decoded_entry is not None:
                    result.append(decoded_entry)

            count_so_far += len(data)
            if meta is None or meta.get('total_count') is None:
                raise RemoteError(
                    f'A bitpanda paginated query for {endpoint} did '
                    f'not contain meta["total_count"]',
                )
            if count_so_far >= meta['total_count']:
                break

            page += 1

        return result  # type: ignore

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            wallets, _, _ = self._api_query('wallets')
            # asset_wallets = self._api_query('asset-wallets')
            fiat_wallets, _, _ = self._api_query('fiatwallets')
        except RemoteError as e:
            msg = f'Failed to query Bitpanda balances. {str(e)}'
            return None, msg

        assets_balance: DefaultDict[AssetWithOracles, Balance] = defaultdict(Balance)
        wallets_len = len(wallets)
        for idx, entry in enumerate(wallets + fiat_wallets):

            if idx < wallets_len:
                symbol_key = 'cryptocoin_symbol'
            else:
                symbol_key = 'fiat_symbol'

            try:
                amount = deserialize_asset_amount(entry['attributes']['balance'])
                asset = asset_from_bitpanda(entry['attributes'][symbol_key])
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown Bitpanda asset {e.identifier}. '
                    f' Ignoring its balance query.',
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
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing Bitpanda balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
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
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        self.first_connection()
        trades = self._query_endpoint_until_end(
            endpoint='trades',
            from_ts=start_ts,
            to_ts=end_ts,
        )
        return trades, (start_ts, end_ts)

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        self.first_connection()
        # Should probably also query wallets/transactions for crypto deposits/withdrawals
        # but it does not seem as if they contain them
        movements = self._query_endpoint_until_end(
            endpoint='fiatwallets/transactions',
            from_ts=start_ts,
            to_ts=end_ts,
        )
        crypto_movements = self._query_endpoint_until_end(
            endpoint='wallets/transactions',
            from_ts=start_ts,
            to_ts=end_ts,
        )
        movements.extend(crypto_movements)
        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for Bitpanda

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for Bitpanda
