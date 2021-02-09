import base64
import hashlib
import hmac
import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from functools import partial
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    overload,
)
from urllib.parse import urlencode

import gevent
import requests
from gevent.lock import Semaphore
from requests.adapters import Response
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_kucoin
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    SystemClockNotSyncedError,
    UnknownAsset,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Location,
    Timestamp,
    TradePair,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE = 400002
# More understandable explanation for API key-related errors than the default `reason`
API_KEY_ERROR_CODE_ACTION = {
    400003: 'Invalid API key value.',
    400004: 'Invalid API passphrase.',
    400005: 'Invalid API secret.',
    400007: 'Provided KuCoin API key needs to have "General" permission activated.',
    411100: 'Contact KuCoin support to unfreeze your account',
}
API_PAGE_SIZE_LIMIT = 500
# Rate limit is 1800 requests per minute, exceed it multiple times the system
# will restrict the IP
API_REQUEST_RETRY_TIMES = 2
API_REQUEST_RETRIES_AFTER_SECONDS = 1


class SkipReason(Enum):
    ABOVE_TIMESTAMP_RANGE = 1
    BELOW_TIMESTAMP_RANGE = 2
    INNER_MOVEMENT = 3

    def __str__(self) -> str:
        if self == SkipReason.ABOVE_TIMESTAMP_RANGE:
            return 'above timestamp range'
        if self == SkipReason.BELOW_TIMESTAMP_RANGE:
            return 'below timestamp range'
        if self == SkipReason.INNER_MOVEMENT:
            return 'that is an inner movement'
        raise AssertionError(f'Unexpected SkipReason: {self}')


DeserializationMethod = Callable[
    ...,
    Union[
        Tuple[Optional[Trade], Optional[SkipReason]],
        Tuple[Optional[AssetMovement], Optional[SkipReason]],
    ],
]  # ... due to keyword args


class Kucoin(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    """Resources:
    https://docs.kucoin.com
    https://github.com/Kucoin/kucoin-python-sdk
    """
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            passphrase: str,
            base_uri: str = 'https://api.kucoin.com',
    ):
        super().__init__(str(Location.KUCOIN), api_key, secret, database)
        self.base_uri = base_uri
        self.session.headers.update({
            'Content-Type': 'application/json',
            'KC-API-KEY': self.api_key,
            'KC-API-PASSPHRASE': passphrase,
            'KC-API-KEY-VERSION': '2',
        })
        self.msg_aggregator = msg_aggregator
        self.nonce_lock = Semaphore()

    def _api_query(
            self,
            endpoint: Literal['accounts', 'deposits', 'fills', 'withdrawals'],
            options: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Request a KuCoin API v1 endpoint

        May raise RemoteError
        """
        call_options = options.copy() if options else {}
        for header in ('KC-API-SIGN', 'KC-API-TIMESTAMP'):
            self.session.headers.pop(header, None)

        if endpoint == 'accounts':
            method = 'get'
            api_path = 'api/v1/accounts'
        elif endpoint == 'deposits':
            method = 'get'
            api_path = 'api/v1/deposits'
        elif endpoint == 'fills':
            method = 'get'
            api_path = 'api/v1/fills'
        elif endpoint == 'withdrawals':
            method = 'get'
            api_path = 'api/v1/withdrawals'
        else:
            raise AssertionError(f'Unexpected endpoint: {endpoint}')

        with self.nonce_lock:
            timestamp = str(ts_now_in_ms())
            request_url = f'{self.base_uri}/{api_path}'
            message = f'{timestamp}{method.upper()}/{api_path}'
            if endpoint in ('deposits', 'fills', 'withdrawals'):
                urlencoded_options = urlencode(call_options)
                request_url = f'{request_url}?{urlencoded_options}'
                message = f'{message}?{urlencoded_options}'

            signature = base64.b64encode(
                hmac.new(
                    self.secret,
                    msg=message.encode('utf-8'),
                    digestmod=hashlib.sha256,
                ).digest(),
            )
            self.session.headers.update({
                'KC-API-SIGN': signature,  # type: ignore # bytes required instead of str
                'KC-API-TIMESTAMP': timestamp,
            })
            log.debug('Kucoin API request', request_url=request_url)
            try:
                response = self.session.request(
                    method=method,
                    url=request_url,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Kucoin {method} request at {request_url} connection error: {str(e)}.',
                ) from e

        return response

    @overload  # noqa: F811
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal['trades'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        ...

    @overload  # noqa: F811
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal['deposits', 'withdrawals'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        ...

    def _api_query_paginated(
            self,
            options: Dict[str, Any],
            case: Literal['trades', 'deposits', 'withdrawals'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Union[List[Trade], List[AssetMovement]]:
        """Request endpoints paginating via an options attribute

        May raise RemoteError and SystemClockNotSyncedError
        """
        endpoint: Literal['fills', 'deposits', 'withdrawals']
        case_: Literal['trades', 'asset_movements']
        deserialization_method: DeserializationMethod
        if case == 'trades':
            endpoint = 'fills'
            case_ = 'trades'
            deserialization_method = self._deserialize_trade
        elif case == 'deposits':
            endpoint = 'deposits'
            case_ = 'asset_movements'
            deserialization_method = partial(
                self._deserialize_asset_movement,
                category_case='deposit',
            )
        elif case == 'withdrawals':
            endpoint = 'withdrawals'
            case_ = 'asset_movements'
            deserialization_method = partial(
                self._deserialize_asset_movement,
                category_case='withdrawal',
            )
        else:
            raise AssertionError(f'Unexpected case: {case}')

        call_options = options.copy()
        results: Union[List[Trade], List[AssetMovement]] = []  # type: ignore # bug list nothing
        retries_left = API_REQUEST_RETRY_TIMES
        retries_after_seconds = API_REQUEST_RETRIES_AFTER_SECONDS
        while retries_left >= 0:
            response = self._api_query(
                endpoint=endpoint,
                options=call_options,
            )
            # Check request rate limit
            if response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS):
                if retries_left == 0:
                    msg = (
                        f'Kucoin {case} request failed after retrying '
                        f'{API_REQUEST_RETRY_TIMES} times.'
                    )
                    self.msg_aggregator.add_error(
                        f'Got remote error while querying kucoin {case}: {msg}',
                    )
                    return []  # type: ignore # bug list nothing

                # Trigger retry
                log.debug(
                    f'Kucoin {case} request reached the rate limits. Backing off',
                    seconds=retries_after_seconds,
                    options=call_options,
                )
                retries_left -= 1
                retries_after_seconds *= 2
                gevent.sleep(retries_after_seconds)
                continue

            if response.status_code != HTTPStatus.OK:
                return self._process_unsuccessful_response(
                    response=response,
                    case=case_,
                )

            try:
                response_dict = rlk_jsonloads_dict(response.text)
            except JSONDecodeError as e:
                msg = f'Kucoin {case} returned an invalid JSON response: {response.text}.'
                log.error(msg)
                self.msg_aggregator.add_error(
                    f'Got remote error while querying kucoin {case}: {msg}',
                )
                raise RemoteError(msg) from e

            try:
                response_data = response_dict['data']
                total_page = response_data['totalPage']
                current_page = response_data['currentPage']
                raw_results = response_data['items']
            except KeyError as e:
                msg = f'Kucoin {case} JSON response is missing key: {str(e)}'
                log.error(msg, response_dict)
                raise RemoteError(msg) from e

            is_below_start_ts = False
            for raw_result in raw_results:
                try:
                    result, skip_reason = deserialization_method(
                        raw_result=raw_result,
                        start_ts=start_ts,
                        end_ts=end_ts,
                    )
                except DeserializationError as e:
                    self.msg_aggregator.add_error(
                        f'{str(e)}. Check logs for more details',
                    )
                    continue

                if result is None and skip_reason is not None:
                    if skip_reason == SkipReason.BELOW_TIMESTAMP_RANGE:
                        log.debug(f'Found a kucoin {case} {str(skip_reason)}. Stop requesting.')
                        break

                    if skip_reason in (
                        SkipReason.ABOVE_TIMESTAMP_RANGE,
                        SkipReason.INNER_MOVEMENT,
                    ):
                        log.debug(f'Found a kucoin {case} {str(skip_reason)}. Skipping it.')
                        continue

                    raise AssertionError(f'Unexpected skip reason: {skip_reason}. Update conditions')  # noqa: E501

                if result is None:
                    # NB: may happen only during development
                    raise AssertionError(f'Unexpected return deserializing {case} calling {endpoint}.')  # noqa: E501

                results.append(result)  # type: ignore # type is known

            # Stop requesting, either when a result was below the range or
            # totalPage indicates to stop paginating
            if is_below_start_ts is True or total_page in (0, current_page):
                break

            # Update pagination params per endpoint
            # NB: Copying the dict before updating it prevents losing the call args values
            call_options = call_options.copy()
            call_options['currentPage'] = current_page + 1
            # break
        return results

    def _calculate_accounts_balances(
            self,
            accounts_data: List[Dict[str, Any]],
    ) -> Dict[Asset, Balance]:
        assets_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for raw_result in accounts_data:
            try:
                amount = FVal(raw_result['balance'])
                if amount == ZERO:
                    continue

                asset_symbol = raw_result['currency']
            except (KeyError, ValueError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key in account: {msg}.'

                log.error(
                    'Failed to deserialize a kucoin account',
                    error=msg,
                    raw_result=raw_result,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kucoin account. Ignoring it.',
                )
                continue

            try:
                asset = asset_from_kucoin(asset_symbol)
            except DeserializationError as e:
                log.error(
                    'Unexpected asset symbol in a kucoin account',
                    error=str(e),
                    raw_result=raw_result,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kucoin account. Ignoring it.',
                )
                continue
            except (UnknownAsset, UnsupportedAsset) as e:
                asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                self.msg_aggregator.add_warning(
                    f'Found {asset_tag} kucoin asset {e.asset_name} while deserializing '
                    f'an account. Ignoring it.',
                )
                continue
            try:
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError:
                self.msg_aggregator.add_error(
                    f'Failed to deserialize a kucoin account balance after failing to '
                    f'request the USD price of {asset.identifier}. Ignoring it.',
                )
                continue

            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance)

    def _check_for_system_clock_not_synced_error(
            self,
            error_code: Optional[int] = None,
    ) -> None:
        if error_code == API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE:
            raise SystemClockNotSyncedError(
                current_time=str(datetime.now()),
                remote_server=f'{self.name}',
            )

    @staticmethod
    def _deserialize_asset_movement(
            raw_result: Dict[str, Any],
            category_case: Literal['deposit', 'withdrawal'],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[Optional[AssetMovement], Optional[SkipReason]]:
        """Process an asset movement result and deserialize it

        May raise DeserializationError
        """
        if category_case == 'deposit':
            category = AssetMovementCategory.DEPOSIT
        elif category_case == 'withdrawal':
            category = AssetMovementCategory.WITHDRAWAL
        else:
            raise AttributeError(f'Unexpected category case: {category_case}')

        try:
            timestamp = deserialize_timestamp(int(raw_result['createdAt'] / 1000))
            if timestamp > end_ts:
                return None, SkipReason.ABOVE_TIMESTAMP_RANGE
            if timestamp < start_ts:
                return None, SkipReason.BELOW_TIMESTAMP_RANGE

            is_inner = raw_result['isInner']
            if is_inner is True:
                return None, SkipReason.INNER_MOVEMENT

            address = raw_result['address']
            transaction_id = raw_result['walletTxId']
            amount = deserialize_asset_amount(raw_result['amount'])
            fee = deserialize_fee(raw_result['fee'])
            fee_currency_symbol = raw_result['currency']
            # NB: id only exists for withdrawals
            link_id = raw_result['id'] if category_case == 'withdrawal' else transaction_id
        except (DeserializationError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in {category_case}: {msg}.'

            log.error(
                f'Failed to deserialize a kucoin {category_case}',
                error=msg,
                raw_result=raw_result,
            )
            raise DeserializationError(f'Failed to deserialize a kucoin {category_case}.') from e

        try:
            fee_asset = asset_from_kucoin(fee_currency_symbol)
        except DeserializationError as e:
            log.error(
                f'Unexpected asset symbol type in a kucoin {category_case}',
                error=str(e),
                raw_result=raw_result,
            )
            raise DeserializationError(f'Failed to deserialize a kucoin {category_case}.') from e
        except (UnknownAsset, UnsupportedAsset) as e:
            asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
            raise DeserializationError(
                f'Found {asset_tag} kucoin asset {e.asset_name} while processing a {category_case}. '  # noqa: E501
                f'Ignoring it.',
            ) from e

        asset_movement = AssetMovement(
            timestamp=timestamp,
            location=Location.KUCOIN,
            category=category,
            address=address,
            transaction_id=transaction_id,
            asset=fee_asset,
            amount=amount,
            fee_asset=fee_asset,
            fee=fee,
            link=link_id,
        )
        return asset_movement, None

    @staticmethod
    def _deserialize_trade(
            raw_result: Dict[str, Any],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[Optional[Trade], Optional[SkipReason]]:
        """Process a trade result and deserialize it

        May raise DeserializationError
        """
        try:
            timestamp = deserialize_timestamp(int(raw_result['createdAt'] / 1000))
            if timestamp > end_ts:
                return None, SkipReason.ABOVE_TIMESTAMP_RANGE
            if timestamp < start_ts:
                return None, SkipReason.BELOW_TIMESTAMP_RANGE

            trade_type = TradeType.BUY if raw_result['side'] == 'buy' else TradeType.SELL
            amount = deserialize_asset_amount(raw_result['size'])
            rate = deserialize_price(raw_result['price'])
            fee = deserialize_fee(raw_result['fee'])
            trade_id = raw_result['tradeId']
            fee_currency_symbol = raw_result['feeCurrency']
            base_asset_symbol, quote_asset_symbol = raw_result['symbol'].split('-')
        except (DeserializationError, KeyError, ValueError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key in trade: {msg}.'

            log.error(
                'Failed to deserialize a kucoin trade',
                error=msg,
                raw_result=raw_result,
            )
            raise DeserializationError('Failed to deserialize a kucoin trade.') from e

        try:
            base_asset = asset_from_kucoin(base_asset_symbol)
            quote_asset = asset_from_kucoin(quote_asset_symbol)
            fee_currency = asset_from_kucoin(fee_currency_symbol)
        except DeserializationError as e:
            log.error(
                'Unexpected asset symbol type in a kucoin trade',
                error=str(e),
                raw_result=raw_result,
            )
            raise DeserializationError('Failed to deserialize a kucoin trade.') from e
        except (UnknownAsset, UnsupportedAsset) as e:
            asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
            raise DeserializationError(
                f'Found {asset_tag} kucoin asset {e.asset_name} while deserializing a trade. '
                f'Ignoring it.',
            ) from e

        trade = Trade(
            timestamp=timestamp,
            location=Location.KUCOIN,
            pair=TradePair(f'{base_asset.identifier}_{quote_asset.identifier}'),
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=trade_id,
            notes='',
        )
        return trade, None

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['validate_api_key'],
    ) -> Tuple[bool, str]:
        ...

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['balances'],
    ) -> ExchangeQueryBalances:
        ...

    @overload  # noqa: F811
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal['trades'],
    ) -> List[Trade]:
        ...

    @overload  # noqa: F811
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
        """Process unsuccessful responses

        May raise RemoteError and SystemClockNotSyncedError
        """
        try:
            response_dict = rlk_jsonloads_dict(response.text)
        except JSONDecodeError as e:
            msg = f'Kucoin {case} returned an invalid JSON response: {response.text}.'
            log.error(msg)

            if case in ('validate_api_key', 'balances'):
                raise RemoteError(msg) from e
            if case in ('trades', 'asset_movements'):
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Kucoin {case}: {msg}',
                )
                return []

            raise AssertionError(f'Unexpected case: {case}') from e

        error_code = response_dict.get('code', None)
        self._check_for_system_clock_not_synced_error(error_code)
        # Errors related with the API key return a human readable message
        if case == 'validate_api_key' and error_code in API_KEY_ERROR_CODE_ACTION.keys():
            return False, API_KEY_ERROR_CODE_ACTION[response_dict['code']]

        # Below any other error not related with the system clock or the API key
        reason = response_dict.get('msg', None) or response.text
        msg = (
            f'Kucoin query responded with error status code: {response.status_code} '
            f'and text: {reason}.'
        )
        log.error(msg)

        if case == 'validate_api_key':
            raise RemoteError(msg)
        if case == 'balances':
            return None, msg
        if case in ('trades', 'asset_movements'):
            self.msg_aggregator.add_error(
                f'Got remote error while querying Kucoin {case}: {msg}',
            )
            return []

        raise AssertionError(f'Unexpected case: {case}')

    def first_connection(self) -> None:
        self.first_connection_made = True

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        """Return the account balances

        May raise RemoteError and SystemClockNotSyncedError
        """
        accounts_response = self._api_query('accounts')
        if accounts_response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=accounts_response,
                case='balances',
            )
            return result, msg

        try:
            response_dict = rlk_jsonloads_dict(accounts_response.text)
        except JSONDecodeError as e:
            msg = f'Kucoin balances returned an invalid JSON response: {accounts_response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        try:
            accounts_data = response_dict['data']
        except KeyError as e:
            msg = 'Kucoin balances JSON response is missing data key'
            log.error(msg, response_dict)
            raise RemoteError(msg) from e

        account_balances = self._calculate_accounts_balances(accounts_data=accounts_data)
        return account_balances, ''

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Return the account deposits and withdrawals

        May raise RemoteError and SystemClockNotSyncedError
        """
        options = {
            'currentPage': 1,
            'pageSize': API_PAGE_SIZE_LIMIT,
            'status': 'SUCCESS',
        }
        asset_movements: List[AssetMovement] = []
        deposits = self._api_query_paginated(
            options=options.copy(),
            case='deposits',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        asset_movements.extend(deposits)
        withdrawals = self._api_query_paginated(
            options=options.copy(),
            case='withdrawals',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        asset_movements.extend(withdrawals)

        return asset_movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Return the account trades

        May raise RemoteError and SystemClockNotSyncedError
        """
        options = {
            'currentPage': 1,
            'pageSize': API_PAGE_SIZE_LIMIT,
            'tradeType': 'TRADE',  # discarded MARGIN_TRADE
        }
        trades: List[Trade] = self._api_query_paginated(
            options=options,
            case='trades',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        return trades

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the KuCoin API key is good for usage in Rotki

        May raise RemoteError and SystemClockNotSyncedError
        """
        response = self._api_query('accounts')

        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case='validate_api_key',
            )
            return result, msg

        return True, ''

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for bitfinex
