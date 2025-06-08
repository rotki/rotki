import hashlib
import hmac
import logging
import uuid
from collections.abc import Sequence
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload
from urllib.parse import urlencode

import requests
from requests.adapters import Response

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.utils import maybe_set_transaction_extra_data
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
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
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_int_from_str,
    deserialize_timestamp_from_bitstamp_date,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ExchangeAuthCredentials,
    Location,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms, ts_sec_to_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


API_ERR_AUTH_NONCE_CODE = 'API0017'
API_ERR_AUTH_NONCE_MESSAGE = (
    'Bitstamp nonce too low error. Is the local system clock in synced?'
)
# More understandable explanation for API key-related errors than the default `reason`
API_KEY_ERROR_CODE_ACTION = {
    'API0001': 'Check your API key value.',
    'API0002': 'The IP address has no permission to use this API key.',
    'API0003': (
        'Provided Bitstamp API key needs to have "Account balance" and "User transactions" '
        'permission activated. Please log into your Bitstamp account and create a key with '
        'the required permissions.'
    ),
    API_ERR_AUTH_NONCE_CODE: API_ERR_AUTH_NONCE_MESSAGE,
    'API0006': 'Contact Bitstamp support to unfreeze your account',
    'API0008': "Can't find a customer with selected API key.",
    'API0011': 'Check that your API key string is correct.',
}
# Max limit for all API v2 endpoints
API_MAX_LIMIT = 1000
# user_transactions endpoint constants
# Sort mode
USER_TRANSACTION_SORTING_MODE = 'asc'
# Starting `since_id`
USER_TRANSACTION_MIN_SINCE_ID = 1
# Trade type int
USER_TRANSACTION_TRADE_TYPE = {2}
# Asset movement type int: 0 - deposit, 1 - withdrawal
USER_TRANSACTION_ASSET_MOVEMENT_TYPE = {0, 1}
KNOWN_NON_ASSET_KEYS_FOR_MOVEMENTS = {
    'datetime',
    'id',
    'type',
    'fee',
}

# We need to query two APIs and then match transactions to get full event history
# There's a problem with matching withdrawals, because one API returns timestamp
# from Activity History, one from Transaction History.
# This is why we added the tolerance to match any transaction that occurred within
# an hour of each other
BITSTAMP_MATCHING_TOLERANCE = 3600


class TradePairData(NamedTuple):
    pair: str
    base_asset_symbol: str
    quote_asset_symbol: str
    base_asset: AssetWithOracles
    quote_asset: AssetWithOracles


class Bitstamp(ExchangeInterface):
    """Bitstamp exchange api docs:
    https://www.bitstamp.net/api/

    An unofficial python bitstamp package:
    https://github.com/kmadac/bitstamp-python-client
    """
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
            location=Location.BITSTAMP,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )
        self.base_uri = 'https://www.bitstamp.net/api'
        # NB: X-Auth-Signature, X-Auth-Nonce, X-Auth-Timestamp & Content-Type change per request
        # X-Auth and X-Auth-Version are constant
        self.session.headers.update({
            'X-Auth': f'BITSTAMP {self.api_key}',
            'X-Auth-Version': 'v2',
        })

    def first_connection(self) -> None:
        self.first_connection_made = True

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        changed = super().edit_exchange_credentials(credentials)
        if credentials.api_key is not None:
            self.session.headers.update({'X-Auth': f'BITSTAMP {credentials.api_key}'})
        return changed

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        """Return the account balances on Bistamp

        The balance endpoint returns a dict where the keys (str) are related to
        assets and the values (str) amounts. The keys that end with `_balance`
        contain the exact amount of an asset the account is holding (available
        amount + orders amount, per asset).
        """
        response = self._api_query('balance')

        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='balances',
            )
            return result, msg
        try:
            response_dict = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            msg = f'Bitstamp returned invalid JSON response: {response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        assets_balance: dict[AssetWithOracles, Balance] = {}
        for entry, raw_amount in response_dict.items():
            if not entry.endswith('_balance'):
                continue

            symbol = entry.split('_')[0]  # If no `_`, defaults to entry
            try:
                amount = deserialize_fval(raw_amount)
                if amount == ZERO:
                    continue
                asset = asset_from_bitstamp(symbol)
            except DeserializationError as e:
                log.error(
                    'Error processing a Bitstamp balance.',
                    entry=entry,
                    error=str(e),
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize a Bitstamp balance. '
                    'Check logs for details. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                log.error(str(e))
                self.msg_aggregator.add_warning(
                    f'Found unsupported Bistamp asset {e.identifier}. Ignoring its balance query.',
                )
                continue
            except UnknownAsset as e:
                self.send_unknown_asset_message(
                    asset_identifier=e.identifier,
                    details='balance query',
                )
                continue
            try:
                usd_price = Inquirer.find_usd_price(asset=asset)
            except RemoteError as e:
                log.error(str(e))
                self.msg_aggregator.add_error(
                    f'Error processing Bitstamp balance result due to inability to '
                    f'query USD price: {e!s}. Skipping balance entry.',
                )
                continue

            assets_balance[asset] = Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return assets_balance, ''

    def _get_since_id_option(
            self,
            start_ts: Timestamp,
            entry_type: HistoryBaseEntryType,
    ) -> dict[str, int]:
        """Retrieves the since_id option from the reference of the latest DB event
        of specified entry type. Returns since_id in a dict or an empty dict if no
        event with a reference exists.
        """
        with self.db.conn.read_ctx() as cursor:
            query_result = cursor.execute(
                'SELECT extra_data FROM history_events WHERE location=? AND timestamp <= ? AND entry_type=? ORDER BY timestamp DESC LIMIT 1',  # noqa: E501
                (Location.BITSTAMP.serialize_for_db(), ts_sec_to_ms(start_ts), entry_type.serialize_for_db()),  # noqa: E501
            ).fetchone()
            if (
                query_result is not None and
                (extra_data := AssetMovement.deserialize_extra_data(
                    entry=query_result,
                    extra_data=query_result[0],
                )) is not None and
                (reference := extra_data.get('reference')) is not None
            ):
                return {'since_id': int(reference) + 1}

        return {}

    def _query_asset_movements(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list['HistoryBaseEntry']:
        """Return the account asset movements on Bitstamp.

        NB: when `since_id` is used, the Bitstamp API v2 will return by default
        1000 entries. However, we make it explicit.
        Bitstamp support confirmed `since_id` at 1 can be used for requesting
        user transactions since the beginning.
        """
        options = {
            'limit': API_MAX_LIMIT,
            'since_id': USER_TRANSACTION_MIN_SINCE_ID,
            'sort': USER_TRANSACTION_SORTING_MODE,
            'offset': 0,
        }
        if start_ts != Timestamp(0):
            options.update(self._get_since_id_option(
                start_ts=start_ts,
                entry_type=HistoryBaseEntryType.ASSET_MOVEMENT_EVENT,
            ))

        # get user transactions (which is deposits/withdrawals) with fees but not address/txid
        asset_movements = self._api_query_paginated(
            end_ts=end_ts,
            options=options,
            case='asset_movements',
        )

        # also query crypto transactions, to get address and transaction id (but no fee)
        with self.db.conn.read_ctx() as cursor:
            offset = 0
            if (result := self.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_CRYPTOTX_OFFSET,
                location=self.location.serialize(),
                location_name=self.name,
            )) is not None:
                offset = result

        crypto_asset_movements = self._query_crypto_transactions(offset)

        # now the fun part. Figure out which asset movements from user transactions
        # they correspond to so we can also have the fee taken into account
        indices_to_delete = []
        for asset_movement in asset_movements:
            if asset_movement.extra_data is None:
                continue  # skip fee events

            for idx, crypto_movement in enumerate(crypto_asset_movements):
                if (
                        crypto_movement.event_type == asset_movement.event_type and
                        crypto_movement.asset == asset_movement.asset and
                        'fee' in asset_movement.extra_data and
                        crypto_movement.amount == asset_movement.amount + asset_movement.extra_data['fee'] and  # noqa: E501
                        abs(crypto_movement.timestamp - asset_movement.timestamp) <= BITSTAMP_MATCHING_TOLERANCE  # noqa: E501
                ):
                    asset_movement.extra_data.update(crypto_movement.extra_data)
                    del asset_movement.extra_data['fee']  # no need to save this to the DB
                    indices_to_delete.append(idx)
                    break

            asset_movement.extra_data.pop('fee', None)  # don't let this get to the DB

        for idx in sorted(indices_to_delete, reverse=True):
            del crypto_asset_movements[idx]  # remove the crypto asset movements whose data we already correlated  # noqa: E501

        # even more fun. If somehow the endpoint is not called in order then we
        # may end up with some crypto asset movements here that would need to
        # check for corresponding asset movement in the DB.
        serialized_location = Location.BITSTAMP.serialize_for_db()
        history_db = DBHistoryEvents(self.db)
        indices_to_delete = []
        with self.db.user_write() as write_cursor:
            for idx, crypto_movement in enumerate(crypto_asset_movements):
                write_cursor.execute(
                    'SELECT * from history_events WHERE location=? AND type=? AND subtype=? AND timestamp=? AND asset=?',  # noqa: E501
                    (serialized_location, crypto_movement.event_type.serialize(), crypto_movement.event_subtype.serialize(), crypto_movement.timestamp, crypto_movement.asset.identifier),  # noqa: E501
                )
                if (result := write_cursor.fetchone()) is not None:
                    try:
                        matched_movement = AssetMovement.deserialize_from_db(entry=result)
                    except (DeserializationError, UnknownAsset) as e:
                        log.error(f'Failed to update extra data for bitstamp asset movement due to {e!s}')  # noqa: E501
                        continue

                    extra_data = matched_movement.extra_data if matched_movement.extra_data is not None else {}  # noqa: E501
                    extra_data.update(crypto_movement.extra_data)  # type: ignore  # crypto_movement.extra_data should always be set here
                    history_db.edit_event_extra_data(
                        write_cursor=write_cursor,
                        event=matched_movement,
                        extra_data=extra_data,
                    )
                    indices_to_delete.append(idx)

        for idx in sorted(indices_to_delete, reverse=True):
            del crypto_asset_movements[idx]  # remove the crypto asset movements whose data we matched in the DB  # noqa: E501

        log.debug(f'Remaining Bitstamp unmatched {crypto_asset_movements=}')
        return asset_movements

    def _query_crypto_transactions(self, offset: int) -> list['HistoryBaseEntry']:
        """Query crypto transactions to get address and transaction id.

        Pagination here is unfortunately primitive. Can only use offset, so we rememmber the
        last offset queried in the DB and after the query update it.

        https://www.bitstamp.net/api/#tag/Transactions-private/operation/GetCryptoUserTransactions

        May raise RemoteError
        """
        options = {}
        options['limit'] = API_MAX_LIMIT
        options['offset'] = offset
        options['include_ious'] = False
        total_asset_movements: list[HistoryBaseEntry] = []

        while True:
            response = self._api_query(
                endpoint='crypto-transactions',
                method='post',
                options=options,
            )
            if response.status_code != HTTPStatus.OK:
                return self._process_unsuccessful_response(
                    response=response,
                    case='crypto-transactions',
                )

            try:
                response_dict = jsonloads_dict(response.text)
            except JSONDecodeError:
                msg = f'Bitstamp returned invalid JSON response: {response.text}.'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Bistamp crypto transactions: {msg}',
                )
                return []

            asset_movements = [
                self._deserialize_asset_movement_from_crypto_transaction(
                    raw_movement=entry,
                    event_type=event_type,  # type: ignore  # will only be deposit or withdrawal
                )
                for entry_key, event_type in [
                    ('deposits', HistoryEventType.DEPOSIT),
                    ('withdrawals', HistoryEventType.WITHDRAWAL),
                ]
                for entry in response_dict.get(entry_key, {})
            ]
            options['offset'] += API_MAX_LIMIT  # add anyway so we can save new offset at end
            total_asset_movements.extend(asset_movements)
            if len(asset_movements) < API_MAX_LIMIT:
                break

        if options['offset'] != offset:
            # write the new offset
            with self.db.user_write() as write_cursor:
                self.db.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_CRYPTOTX_OFFSET,
                    value=options['offset'],
                    location=self.location.serialize(),
                    location_name=self.name,
                )

        return total_asset_movements

    def _query_trades(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list['HistoryBaseEntry']:
        """Return the account trades on Bitstamp.

        NB: when `since_id` is used, the Bitstamp API v2 will return by default
        1000 entries. However, we make it explicit.
        Bitstamp support confirmed `since_id` at 1 can be used for requesting
        user transactions since the beginning.
        """
        options = {
            'limit': API_MAX_LIMIT,
            'since_id': USER_TRANSACTION_MIN_SINCE_ID,
            'sort': USER_TRANSACTION_SORTING_MODE,
            'offset': 0,
        }
        if start_ts != Timestamp(0):
            options.update(self._get_since_id_option(
                start_ts=start_ts,
                entry_type=HistoryBaseEntryType.SWAP_EVENT,
            ))

        return self._api_query_paginated(
            end_ts=end_ts,
            options=options,
            case='trades',
        )

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[Sequence['HistoryBaseEntry'], Timestamp]:
        events = self._query_asset_movements(
            start_ts=start_ts,
            end_ts=end_ts,
        )
        events.extend(self._query_trades(
            start_ts=start_ts,
            end_ts=end_ts,
        ))
        return events, end_ts

    def validate_api_key(self) -> tuple[bool, str]:
        """Validates that the Bitstamp API key is good for usage in rotki

        Makes sure that the following permissions are given to the key:
        - Account balance
        - User transactions
        """
        response = self._api_query('balance')

        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='validate_api_key',
            )
            return result, msg

        return True, ''

    def _api_query(
            self,
            endpoint: Literal['balance', 'user_transactions', 'crypto-transactions'],
            method: Literal['post'] = 'post',
            options: dict[str, Any] | None = None,
    ) -> Response:
        """Request a Bistamp API v2 endpoint (from `endpoint`).

        May raise RemoteError
        """
        call_options = options.copy() if options else {}
        data = call_options or None
        request_url = f'{self.base_uri}/v2/{endpoint}/'
        query_params = ''
        nonce = str(uuid.uuid4())
        timestamp = str(ts_now_in_ms())
        payload_string = urlencode(call_options)
        content_type = '' if payload_string == '' else 'application/x-www-form-urlencoded'
        message = (
            'BITSTAMP '
            f'{self.api_key}'
            f'{method.upper()}'
            f'{request_url.replace("https://", "")}'
            f'{query_params}'
            f'{content_type}'
            f'{nonce}'
            f'{timestamp}'
            'v2'
            f'{payload_string}'
        )
        signature = hmac.new(
            self.secret,
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

        self.session.headers.update({
            'X-Auth-Signature': signature,
            'X-Auth-Nonce': nonce,
            'X-Auth-Timestamp': timestamp,
        })
        if content_type:
            self.session.headers.update({'Content-Type': content_type})
        else:
            self.session.headers.pop('Content-Type', None)

        log.debug('Bitstamp API request', request_url=request_url, options=options)
        try:
            response = self.session.request(
                method=method,
                url=request_url,
                data=data,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(
                f'Bitstamp {method} request at {request_url} connection error: {e!s}.',
            ) from e

        return response

    def _api_query_paginated(
            self,
            end_ts: Timestamp,
            options: dict[str, Any],
            case: Literal['trades', 'asset_movements'],
            offset: int = 0,
    ) -> list['HistoryBaseEntry']:
        """Request a Bitstamp API v2 endpoint paginating via an options
        attribute.

        Currently it targets the "user_transactions" endpoint. For supporting
        other endpoints some amendments should be done (e.g. request method,
        loop that processes entities).

        Pagination attribute criteria per endpoint:
          - user_transactions:
            * since_id: from <Trade>.id + 1 (if db trade exists), else 1
            * limit: 1000 (API v2 default using `since_id`).
            * sort: 'asc'
        """
        deserialization_method: Callable[[dict[str, Any]], list[SwapEvent] | list[AssetMovement]]
        endpoint: Literal['user_transactions']
        response_case: Literal['trades', 'asset_movements']
        if case == 'trades':
            endpoint = 'user_transactions'
            raw_result_type_filter = USER_TRANSACTION_TRADE_TYPE
            response_case = 'trades'
            case_pretty = 'trade'
            deserialization_method = self._deserialize_trade
        elif case == 'asset_movements':
            endpoint = 'user_transactions'
            raw_result_type_filter = USER_TRANSACTION_ASSET_MOVEMENT_TYPE
            response_case = 'asset_movements'
            case_pretty = 'asset movement'
            deserialization_method = self._deserialize_asset_movement_from_user_transaction
        else:
            raise AssertionError(f'Unexpected Bitstamp case: {case}.')

        # Check required options per endpoint
        if endpoint == 'user_transactions':
            assert options['limit'] == API_MAX_LIMIT
            assert options['since_id'] >= USER_TRANSACTION_MIN_SINCE_ID
            assert options['sort'] == USER_TRANSACTION_SORTING_MODE
            assert options['offset'] == 0

        call_options = options.copy()
        limit = options.get('limit', API_MAX_LIMIT)
        results: list[HistoryBaseEntry] = []
        while True:
            response = self._api_query(
                endpoint=endpoint,
                method='post',
                options=call_options,
            )
            if response.status_code != HTTPStatus.OK:
                return self._process_unsuccessful_response(
                    response=response,
                    case=response_case,
                )
            try:
                response_list = jsonloads_list(response.text)
            except JSONDecodeError:
                msg = f'Bitstamp returned invalid JSON response: {response.text}.'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Bistamp trades: {msg}',
                )
                return []

            has_results = False
            is_result_timestamp_gt_end_ts = False
            result: list[SwapEvent] | list[AssetMovement]
            for raw_result in response_list:
                try:
                    entry_type = deserialize_int_from_str(raw_result['type'], 'bitstamp event')
                    if entry_type not in raw_result_type_filter:
                        log.debug(f'Skipping entry {raw_result} due to type mismatch')
                        continue
                    result_timestamp = deserialize_timestamp_from_bitstamp_date(
                        raw_result['datetime'],
                    )

                    if result_timestamp > end_ts:
                        is_result_timestamp_gt_end_ts = True  # prevent extra request
                        break

                    log.debug(f'Attempting to deserialize bitstamp {case_pretty}: {raw_result}')
                    result = deserialization_method(raw_result)

                except DeserializationError as e:
                    msg = str(e)
                    log.error(
                        f'Error processing a Bitstamp {case_pretty}.',
                        raw_result=raw_result,
                        error=msg,
                    )
                    self.msg_aggregator.add_error(
                        f'Failed to deserialize a Bitstamp {case_pretty}. '
                        f'Check logs for details. Ignoring it.',
                    )
                    continue

                results.extend(result)
                has_results = True  # NB: endpoint agnostic

            if len(response_list) < limit or is_result_timestamp_gt_end_ts:
                break

            # NB: update pagination params per endpoint
            if endpoint == 'user_transactions':
                # NB: re-assign dict instead of update, prevent lose call args values
                call_options = call_options.copy()
                offset = 0 if has_results else call_options['offset'] + API_MAX_LIMIT
                # If has_results is true then _deserialize_trade and create_swap_events returned
                # successfully which guarantees at least one full group of SwapEvents will be
                # present (either 2 events: spend, receive; or 3 events: spend, receive, fee).
                since_id = (
                    int((results[-2].extra_data or results[-3].extra_data)['reference']) + 1  # type: ignore[index]  # the spend event will always have extra_data
                    if has_results else call_options['since_id']
                )
                call_options.update({
                    'since_id': since_id,
                    'offset': offset,
                })

        return results

    def _deserialize_asset_movement_from_user_transaction(
            self,
            raw_movement: dict[str, Any],
    ) -> list[AssetMovement]:
        """Process a deposit/withdrawal user transaction from Bitstamp and
        deserialize it.

        Can raise DeserializationError.

        From Bitstamp documentation, deposits/withdrawals can have a fee
        (the amount is expected to be in the currency involved)
        https://www.bitstamp.net/fee-schedule/

        Endpoint docs:
        https://www.bitstamp.net/api/#user-transactions
        """
        type_ = deserialize_int_from_str(raw_movement['type'], 'bitstamp asset movement')
        event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]
        if type_ == 0:
            event_type = HistoryEventType.DEPOSIT
        elif type_ == 1:
            event_type = HistoryEventType.WITHDRAWAL
        else:
            raise AssertionError(f'Unexpected Bitstamp asset movement case: {type_}.')

        timestamp = ts_sec_to_ms(deserialize_timestamp_from_bitstamp_date(raw_movement['datetime']))  # noqa: E501
        amount: FVal = ZERO
        fee_asset: AssetWithOracles | None = None
        for raw_movement_key, value in raw_movement.items():
            if raw_movement_key in KNOWN_NON_ASSET_KEYS_FOR_MOVEMENTS:
                continue
            try:
                candidate_fee_asset = asset_from_bitstamp(raw_movement_key)
            except (UnknownAsset, DeserializationError):
                continue
            try:
                amount = deserialize_fval(value)
            except DeserializationError:
                continue
            if amount != ZERO:
                fee_asset = candidate_fee_asset
                break

        if amount == ZERO or fee_asset is None:
            raise DeserializationError(
                'Could not deserialize Bitstamp asset movement from user transaction. '
                f'Unexpected asset amount combination found in: {raw_movement}.',
            )

        # TODO: Improve the logic combining these with the ones from the crypto_transaction query.
        # Using this temporary fee entry in the extra_data is rather hacky.
        # See: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=90720824
        return create_asset_movement_with_fee(
            location=self.location,
            location_label=self.name,
            event_type=event_type,
            timestamp=timestamp,
            asset=fee_asset,
            amount=abs(amount),
            fee=AssetAmount(
                asset=fee_asset,
                amount=(fee := deserialize_fval_or_zero(raw_movement['fee'])),
            ),
            unique_id=(reference := str(raw_movement['id'])),
            extra_data={
                'reference': reference,
                'fee': fee,
            },
        )

    @staticmethod
    def _deserialize_asset_movement_from_crypto_transaction(
            raw_movement: dict[str, Any],
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
    ) -> AssetMovement:
        """Process a deposit/withdrawal crypto transaction from Bitstamp and
        deserialize it.

        Can raise DeserializationError.

        https://www.bitstamp.net/api/#tag/Transactions-private/operation/GetCryptoUserTransactions
        """

        try:
            timestamp = Timestamp(raw_movement['datetime'])
            asset = asset_from_bitstamp(raw_movement['currency'])
            amount = deserialize_fval(raw_movement['amount'])
            address = raw_movement['destinationAddress']
            transaction_id = raw_movement['txid']
        except KeyError as e:
            raise DeserializationError(f'Could not find key {e} in bitstramp crypto transaction') from e  # noqa: E501

        return AssetMovement(
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.BITSTAMP,
            event_type=event_type,
            asset=asset,
            amount=abs(amount),
            unique_id=transaction_id,
            extra_data=maybe_set_transaction_extra_data(
                address=address,
                transaction_id=transaction_id,
            ),
        )

    def _deserialize_trade(
            self,
            raw_trade: dict[str, Any],
    ) -> list[SwapEvent]:
        """Process a raw trade from Bitstamp and deserialize it into a list of SwapEvents.

        Can raise DeserializationError.
        """
        trade_pair_data = self._get_trade_pair_data_from_transaction(raw_trade)
        base_asset_amount = deserialize_fval(
            raw_trade[trade_pair_data.base_asset_symbol],
        )
        quote_asset_amount = deserialize_fval(
            raw_trade[trade_pair_data.quote_asset_symbol],
        )
        if base_asset_amount < ZERO and quote_asset_amount < ZERO:
            raise DeserializationError(
                f'Unexpected bitstamp trade format. Both base and quote '
                f'amounts are negative: {raw_trade}',
            )

        spend, receive = get_swap_spend_receive(
            is_buy=base_asset_amount >= ZERO,
            base_asset=trade_pair_data.base_asset,
            quote_asset=trade_pair_data.quote_asset,
            amount=abs(base_asset_amount),
            rate=deserialize_price(raw_trade[trade_pair_data.pair]),
        )
        return create_swap_events(
            timestamp=ts_sec_to_ms(deserialize_timestamp_from_bitstamp_date(raw_trade['datetime'])),
            location=self.location,
            spend=spend,
            receive=receive,
            fee=AssetAmount(
                asset=trade_pair_data.quote_asset,
                amount=deserialize_fval_or_zero(raw_trade['fee']),
            ),
            location_label=self.name,
            event_identifier=create_event_identifier_from_unique_id(
                location=self.location,
                unique_id=(reference := str(raw_trade['id'])),
            ),
            extra_data={'reference': reference},
        )

    @staticmethod
    def _get_trade_pair_data_from_transaction(raw_result: dict[str, Any]) -> TradePairData:
        """Given a user transaction that contains the base and quote assets'
        symbol as keys, return the Bitstamp trade pair data (raw pair str,
        base/quote assets raw symbols, and TradePair).

        NB: any custom pair conversion (e.g. from Bitstamp asset symbol to world)
        should happen here.

        Can raise DeserializationError.
        """
        try:
            pair = next(key for key in raw_result if '_' in key and key != 'order_id')
        except IndexError as e:
            raise DeserializationError(
                'Could not deserialize Bitstamp trade pair from user transaction. '
                f'Trade pair not found in: {raw_result}.',
            ) from e

        # NB: `pair_get_assets()` is not used for simplifying the calls and
        # storing the raw pair strings.
        base_asset_symbol, quote_asset_symbol = pair.split('_')
        try:
            base_asset = asset_from_bitstamp(base_asset_symbol)
            quote_asset = asset_from_bitstamp(quote_asset_symbol)
        except (UnknownAsset, UnsupportedAsset) as e:
            log.error(str(e))
            asset_tag = 'Unknown' if isinstance(e, UnknownAsset) else 'Unsupported'
            raise DeserializationError(
                f'{asset_tag} {e.identifier} found while processing trade pair.',
            ) from e

        return TradePairData(
            pair=pair,
            base_asset_symbol=base_asset_symbol,
            quote_asset_symbol=quote_asset_symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
        )

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key'],
    ) -> tuple[bool, str]:
        ...

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['balances'],
    ) -> ExchangeQueryBalances:
        ...

    @overload
    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['trades', 'asset_movements', 'crypto-transactions'],
    ) -> list['HistoryBaseEntry']:
        ...

    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key', 'balances', 'trades', 'asset_movements', 'crypto-transactions'],  # noqa: E501
    ) -> list | (tuple[bool, str] | ExchangeQueryBalances):
        """This function processes not successful responses for the following
        cases listed in `case`.
        """
        case_pretty = case.replace('_', ' ')  # human readable case
        try:
            response_dict = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            msg = f'Bitstamp returned invalid JSON response: {response.text}.'
            log.error(msg)

            if case in {'validate_api_key', 'balances'}:
                return False, msg
            if case in {'trades', 'asset_movements', 'crypto-transactions'}:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Bistamp {case_pretty}: {msg}',
                )
                return []

            raise AssertionError(f'Unexpected Bitstamp response_case: {case}.') from e

        error_code = response_dict.get('code', None)
        if error_code in API_KEY_ERROR_CODE_ACTION:
            msg = API_KEY_ERROR_CODE_ACTION[error_code]
        else:
            reason = response_dict.get('reason', None) or response.text
            msg = (
                f'Bitstamp query responded with error status code: {response.status_code} '
                f'and text: {reason}.'
            )
            log.error(msg)

        if case in {'validate_api_key', 'balances'}:
            return False, msg
        if case in {'trades', 'asset_movements', 'crypto-transactions'}:
            self.msg_aggregator.add_error(
                f'Got remote error while querying Bistamp {case_pretty}: {msg}',
            )
            return []

        raise AssertionError(f'Unexpected Bitstamp response_case: {case}.')

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
        return []  # noop for bitstamp
