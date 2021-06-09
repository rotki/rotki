import hashlib
import hmac
import logging
import uuid
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
    overload,
)
from urllib.parse import urlencode

import requests
from requests.adapters import Response
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_bitstamp
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    AssetMovementCategory,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_int_from_str,
    deserialize_timestamp_from_bitstamp_date,
)
from rotkehlchen.typing import ApiKey, ApiSecret, AssetAmount, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict, jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

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

# from https://www.bitstamp.net/api/#user-transactions
BITSTAMP_ASSET_MOVEMENT_SYMBOLS = (
    'usd',
    'eur',
    'btc',
    'xrp',
    'gbp',
    'ltc',
    'eth',
    'bch',
    'xlm',
    'pax',
    'link',
    'omg',
    'usdc',
)


class TradePairData(NamedTuple):
    pair: str
    base_asset_symbol: str
    quote_asset_symbol: str
    base_asset: Asset
    quote_asset: Asset


class Bitstamp(ExchangeInterface):  # lgtm[py/missing-call-to-init]
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
        )
        self.base_uri = 'https://www.bitstamp.net/api'
        self.msg_aggregator = msg_aggregator
        # NB: X-Auth-Signature, X-Auth-Nonce, X-Auth-Timestamp & Content-Type change per request
        # X-Auth and X-Auth-Version are constant
        self.session.headers.update({
            'X-Auth': f'BITSTAMP {self.api_key}',
            'X-Auth-Version': 'v2',
        })

    def first_connection(self) -> None:
        self.first_connection_made = True

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'X-Auth': f'BITSTAMP {api_key}'})
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

        assets_balance: Dict[Asset, Balance] = {}
        for entry, amount in response_dict.items():
            if not entry.endswith('_balance'):
                continue

            symbol = entry.split('_')[0]  # If no `_`, defaults to entry
            try:
                amount = deserialize_asset_amount(amount)
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
            except (UnknownAsset, UnsupportedAsset) as e:
                log.error(str(e))
                asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                self.msg_aggregator.add_warning(
                    f'Found {asset_tag} Bistamp asset {e.asset_name}. Ignoring its balance query.',
                )
                continue
            try:
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError as e:
                log.error(str(e))
                self.msg_aggregator.add_error(
                    f'Error processing Bitstamp balance result due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry.',
                )
                continue

            assets_balance[asset] = Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return assets_balance, ''

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
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
            db_asset_movements = self.db.get_asset_movements(
                to_ts=start_ts,
                location=Location.BITSTAMP,
            )
            # NB: sort asset_movements by int(link) in asc mode
            db_asset_movements.sort(key=lambda asset_movement: int(asset_movement.link))
            if db_asset_movements:
                options.update({'since_id': int(db_asset_movements[-1].link) + 1})

        asset_movements: List[AssetMovement] = self._api_query_paginated(
            start_ts=start_ts,
            end_ts=end_ts,
            options=options,
            case='asset_movements',
        )
        return asset_movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
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
            db_trades = self.db.get_trades(
                to_ts=start_ts,
                location=Location.BITSTAMP,
            )
            # NB: sort trades by int(link) in asc mode. Type ignore is since we always got a link
            db_trades.sort(key=lambda trade: int(trade.link))  # type: ignore
            if db_trades:
                options.update({'since_id': int(db_trades[-1].link) + 1})  # type: ignore

        trades: List[Trade] = self._api_query_paginated(
            start_ts=start_ts,
            end_ts=end_ts,
            options=options,
            case='trades',
        )
        return trades

    def validate_api_key(self) -> Tuple[bool, str]:
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
            endpoint: Literal['balance', 'user_transactions'],
            method: Literal['post'] = 'post',
            options: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Request a Bistamp API v2 endpoint (from `endpoint`).
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
                f'Bitstamp {method} request at {request_url} connection error: {str(e)}.',
            ) from e

        return response

    @overload
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            options: Dict[str, Any],
            case: Literal['trades'],
    ) -> List[Trade]:
        ...

    @overload
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            options: Dict[str, Any],
            case: Literal['asset_movements'],
    ) -> List[AssetMovement]:
        ...

    def _api_query_paginated(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
            options: Dict[str, Any],
            case: Literal['trades', 'asset_movements'],
    ) -> Union[List[Trade], List[AssetMovement]]:
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
        deserialization_method: Callable[[Dict[str, Any]], Union[Trade, AssetMovement]]
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
            deserialization_method = self._deserialize_asset_movement
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
        results: Union[List[Trade], List[AssetMovement]] = []  # type: ignore
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
                no_results: Union[List[Trade], List[AssetMovement]] = []  # type: ignore
                return no_results

            has_results = False
            is_result_timestamp_gt_end_ts = False
            result: Union[Trade, AssetMovement]
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

                results.append(result)  # type: ignore
                has_results = True  # NB: endpoint agnostic

            if len(response_list) < limit or is_result_timestamp_gt_end_ts:
                break

            # NB: update pagination params per endpoint
            if endpoint == 'user_transactions':
                # NB: re-assign dict instead of update, prevent lose call args values
                call_options = call_options.copy()
                offset = 0 if has_results else call_options['offset'] + API_MAX_LIMIT
                since_id = int(results[-1].link) + 1 if has_results else call_options['since_id']  # type: ignore # noqa: E501 # we always got a link in bitstamp trades
                call_options.update({
                    'since_id': since_id,
                    'offset': offset,
                })

        return results

    @staticmethod
    def _deserialize_asset_movement(
            raw_movement: Dict[str, Any],
    ) -> AssetMovement:
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
        category: AssetMovementCategory
        if type_ == 0:
            category = AssetMovementCategory.DEPOSIT
        elif type_ == 1:
            category = AssetMovementCategory.WITHDRAWAL
        else:
            raise AssertionError(f'Unexpected Bitstamp asset movement case: {type_}.')

        timestamp = deserialize_timestamp_from_bitstamp_date(raw_movement['datetime'])
        amount: FVal
        fee_asset: Asset
        for symbol in BITSTAMP_ASSET_MOVEMENT_SYMBOLS:
            amount = deserialize_asset_amount(raw_movement.get(symbol, '0'))
            if amount != ZERO:
                fee_asset = Asset(symbol)
                break

        if amount == ZERO:
            raise DeserializationError(
                'Could not deserialize Bitstamp asset movement from user transaction. '
                f'Unexpected asset amount combination found in: {raw_movement}.',
            )

        asset_movement = AssetMovement(
            timestamp=timestamp,
            location=Location.BITSTAMP,
            category=category,
            address=None,  # requires query "crypto_transactions" endpoint
            transaction_id=None,  # requires query "crypto_transactions" endpoint
            asset=fee_asset,
            amount=abs(amount),
            fee_asset=fee_asset,
            fee=deserialize_fee(raw_movement['fee']),
            link=str(raw_movement['id']),
        )
        return asset_movement

    def _deserialize_trade(
            self,
            raw_trade: Dict[str, Any],
    ) -> Trade:
        """Process a trade user transaction from Bitstamp and deserialize it.

        Can raise DeserializationError.
        """
        timestamp = deserialize_timestamp_from_bitstamp_date(raw_trade['datetime'])
        trade_pair_data = self._get_trade_pair_data_from_transaction(raw_trade)
        base_asset_amount = deserialize_asset_amount(
            raw_trade[trade_pair_data.base_asset_symbol],
        )
        quote_asset_amount = deserialize_asset_amount(
            raw_trade[trade_pair_data.quote_asset_symbol],
        )
        rate = deserialize_price(raw_trade[trade_pair_data.pair])
        fee_currency = trade_pair_data.quote_asset
        if base_asset_amount >= ZERO:
            trade_type = TradeType.BUY
        else:
            if quote_asset_amount < 0:
                raise DeserializationError(
                    f'Unexpected bitstamp trade format. Both base and quote '
                    f'amounts are negative: {raw_trade}',
                )
            trade_type = TradeType.SELL

        trade = Trade(
            timestamp=timestamp,
            location=Location.BITSTAMP,
            base_asset=trade_pair_data.base_asset,
            quote_asset=trade_pair_data.quote_asset,
            trade_type=trade_type,
            amount=AssetAmount(abs(base_asset_amount)),
            rate=rate,
            fee=deserialize_fee(raw_trade['fee']),
            fee_currency=fee_currency,
            link=str(raw_trade['id']),
            notes='',
        )
        return trade

    @staticmethod
    def _get_trade_pair_data_from_transaction(raw_result: Dict[str, Any]) -> TradePairData:
        """Given a user transaction that contains the base and quote assets'
        symbol as keys, return the Bitstamp trade pair data (raw pair str,
        base/quote assets raw symbols, and TradePair).

        NB: any custom pair conversion (e.g. from Bitstamp asset symbol to world)
        should happen here.

        Can raise DeserializationError.
        """
        try:
            pair = [key for key in raw_result.keys() if '_' in key and key != 'order_id'][0]
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
                f'{asset_tag} {e.asset_name} found while processing trade pair.',
            ) from e

        return TradePairData(
            pair=pair,
            base_asset_symbol=base_asset_symbol,
            quote_asset_symbol=quote_asset_symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
        )

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['validate_api_key'],
    ) -> Tuple[bool, str]:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['balances'],
    ) -> ExchangeQueryBalances:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['trades'],
    ) -> List[Trade]:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['asset_movements'],
    ) -> List[AssetMovement]:
        ...

    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal['validate_api_key', 'balances', 'trades', 'asset_movements'],
    ) -> Union[
        List,
        Tuple[bool, str],
        ExchangeQueryBalances,
    ]:
        """This function processes not successful responses for the following
        cases listed in `case`.
        """
        case_pretty = case.replace('_', ' ')  # human readable case
        try:
            response_dict = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            msg = f'Bitstamp returned invalid JSON response: {response.text}.'
            log.error(msg)

            if case in ('validate_api_key', 'balances'):
                return False, msg
            if case in ('trades', 'asset_movements'):
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Bistamp {case_pretty}: {msg}',
                )
                return []

            raise AssertionError(f'Unexpected Bitstamp response_case: {case}.') from e

        error_code = response_dict.get('code', None)
        if error_code in set(API_KEY_ERROR_CODE_ACTION.keys()):
            msg = API_KEY_ERROR_CODE_ACTION[error_code]
        else:
            reason = response_dict.get('reason', None) or response.text
            msg = (
                f'Bitstamp query responded with error status code: {response.status_code} '
                f'and text: {reason}.'
            )
            log.error(msg)

        if case in ('validate_api_key', 'balances'):
            return False, msg
        if case in ('trades', 'asset_movements'):
            self.msg_aggregator.add_error(
                f'Got remote error while querying Bistamp {case_pretty}: {msg}',
            )
            return []

        raise AssertionError(f'Unexpected Bitstamp response_case: {case}.')

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for bitstamp
