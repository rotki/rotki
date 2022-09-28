import base64
import hashlib
import hmac
import logging
from collections import defaultdict
from enum import Enum, auto
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
    Literal,
    Optional,
    Tuple,
    Union,
    overload,
)
from urllib.parse import urlencode

import gevent
import requests
from requests.adapters import Response

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_kucoin
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, MONTH_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_int_from_str,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Location,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE = 400002
# More understandable explanation for API key-related errors than the default `reason`
API_KEY_ERROR_CODE_ACTION = {
    API_SYSTEM_CLOCK_NOT_SYNCED_ERROR_CODE: 'Invalid timestamp. Is your system clock synced?',
    400003: 'Invalid API key value.',
    400004: 'Invalid API passphrase.',
    400005: 'Invalid API secret.',
    400007: 'Provided KuCoin API key needs to have "General" permission activated.',
    400100: 'Invalid query time',
    411100: 'Contact KuCoin support to unfreeze your account',
}
API_PAGE_SIZE_LIMIT = 500
# Once the rate limit is exceeded, the system will restrict your use of your IP or account for 10s.
# https://docs.kucoin.com/#request-rate-limit
API_REQUEST_RETRY_TIMES = 4
API_REQUEST_RETRIES_AFTER_SECONDS = 10

API_V2_TIMESTART = Timestamp(1550448000)  # 2019-02-18T00:00:00Z
API_V2_TIMESTART_MS = API_V2_TIMESTART * 1000
KUCOIN_LAUNCH_TS = Timestamp(1504224000)  # 01/09/2017


class KucoinCase(Enum):
    API_KEY = auto()
    BALANCES = auto()
    TRADES = auto()
    OLD_TRADES = auto()
    DEPOSITS = auto()
    WITHDRAWALS = auto()

    def __str__(self) -> str:
        if self == KucoinCase.API_KEY:
            return 'api_key'
        if self == KucoinCase.BALANCES:
            return 'balances'
        if self == KucoinCase.TRADES:
            return 'trades'
        if self == KucoinCase.OLD_TRADES:
            return 'old trades'
        if self == KucoinCase.DEPOSITS:
            return 'deposits'
        if self == KucoinCase.WITHDRAWALS:
            return 'withdrawals'
        raise AssertionError(f'Unexpected KucoinCase: {self}')


PAGINATED_CASES = (KucoinCase.OLD_TRADES, KucoinCase.TRADES, KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS)  # noqa: E501


def _deserialize_ts(case: KucoinCase, time: int) -> Timestamp:
    if case == KucoinCase.OLD_TRADES:
        return Timestamp(time)
    return Timestamp(int(time / 1000))


DeserializationMethod = Callable[..., Union[Trade, AssetMovement]]


def deserialize_trade_pair(trade_pair_symbol: str) -> Tuple[AssetWithOracles, AssetWithOracles]:
    """May raise:
    - UnprocessableTradePair
    - UnknownAsset
    - UnsupportedAsset
    """
    try:
        base_asset_symbol, quote_asset_symbol = trade_pair_symbol.split('-')
    except ValueError as e:
        raise UnprocessableTradePair(trade_pair_symbol) from e

    base_asset = asset_from_kucoin(base_asset_symbol)
    quote_asset = asset_from_kucoin(quote_asset_symbol)

    return base_asset, quote_asset


class Kucoin(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    """Resources:
    https://docs.kucoin.com
    https://github.com/Kucoin/kucoin-python-sdk
    """
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            passphrase: str,
            base_uri: str = 'https://api.kucoin.com',
    ):
        super().__init__(
            name=name,
            location=Location.KUCOIN,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.base_uri = base_uri
        self.api_passphrase = passphrase
        self.session.headers.update({
            'Content-Type': 'application/json',
            'KC-API-KEY': self.api_key,
            'KC-API-KEY-VERSION': '2',
        })
        self.msg_aggregator = msg_aggregator

    def update_passphrase(self, new_passphrase: str) -> None:
        self.api_passphrase = new_passphrase

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'KC-API-KEY': self.api_key})
        if passphrase is not None:
            self.update_passphrase(passphrase)

        return changed

    def _api_query(
            self,
            case: KucoinCase,
            options: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Request a KuCoin API v1 endpoint

        May raise RemoteError
        """
        call_options = options.copy() if options else {}
        for header in ('KC-API-SIGN', 'KC-API-TIMESTAMP', 'KC-API-PASSPHRASE'):
            self.session.headers.pop(header, None)

        if case == KucoinCase.BALANCES:
            api_path = 'api/v1/accounts'
        elif case == KucoinCase.DEPOSITS:
            assert isinstance(options, dict)
            if options['startAt'] < API_V2_TIMESTART_MS:
                api_path = 'api/v1/hist-deposits'
            else:
                api_path = 'api/v1/deposits'
        elif case == KucoinCase.WITHDRAWALS:
            assert isinstance(options, dict)
            if options['startAt'] < API_V2_TIMESTART_MS:
                api_path = 'api/v1/hist-withdrawals'
            else:
                api_path = 'api/v1/withdrawals'
        elif case == KucoinCase.OLD_TRADES:
            assert isinstance(options, dict)
            api_path = 'api/v1/orders'
        elif case == KucoinCase.TRADES:
            assert isinstance(options, dict)
            api_path = 'api/v1/fills'
        else:
            raise AssertionError(f'Unexpected case: {case}')

        retries_left = API_REQUEST_RETRY_TIMES
        retries_after_seconds = API_REQUEST_RETRIES_AFTER_SECONDS
        while retries_left >= 0:
            timestamp = str(ts_now_in_ms())
            method = 'GET'
            request_url = f'{self.base_uri}/{api_path}'
            message = f'{timestamp}{method}/{api_path}'
            if case in PAGINATED_CASES:
                if call_options != {}:
                    urlencoded_options = urlencode(call_options)
                    request_url = f'{request_url}?{urlencoded_options}'
                    message = f'{message}?{urlencoded_options}'

            signature = base64.b64encode(
                hmac.new(
                    self.secret,
                    msg=message.encode('utf-8'),
                    digestmod=hashlib.sha256,
                ).digest(),
            ).decode('utf-8')
            passphrase = base64.b64encode(hmac.new(
                self.secret,
                self.api_passphrase.encode('utf-8'),
                hashlib.sha256,
            ).digest()).decode('utf-8')
            self.session.headers.update({
                'KC-API-SIGN': signature,
                'KC-API-TIMESTAMP': timestamp,
                'KC-API-PASSPHRASE': passphrase,
            })
            log.debug('Kucoin API request', request_url=request_url)
            try:
                response = self.session.get(url=request_url, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Kucoin {method} request at {request_url} connection error: {str(e)}.',
                ) from e

            log.debug('Kucoin API response', text=response.text)
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
                    return response

                # Trigger retry
                log.debug(
                    f'Kucoin {case} request reached the rate limits. Backing off',
                    seconds=retries_after_seconds,
                    options=call_options,
                )
                retries_left -= 1
                gevent.sleep(retries_after_seconds)
                retries_after_seconds *= 2
                continue

            break

        return response

    @overload
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal[KucoinCase.OLD_TRADES, KucoinCase.TRADES],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        ...

    @overload
    def _api_query_paginated(  # pylint: disable=no-self-use
            self,
            options: Dict[str, Any],
            case: Literal[KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        ...

    def _api_query_paginated(
            self,
            options: Dict[str, Any],
            case: Literal[
                KucoinCase.TRADES,
                KucoinCase.OLD_TRADES,
                KucoinCase.DEPOSITS,
                KucoinCase.WITHDRAWALS,
            ],
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Union[List[Trade], List[AssetMovement]]:
        """Request endpoints paginating via an options attribute

        May raise RemoteError
        """
        results = []
        deserialization_method: DeserializationMethod
        if case == KucoinCase.TRADES:
            if start_ts < API_V2_TIMESTART:
                # create separate query for v1 trades.
                results.extend(self._api_query_paginated(
                    options=options,
                    case=KucoinCase.OLD_TRADES,
                    start_ts=start_ts,
                    end_ts=API_V2_TIMESTART,
                ))
                if end_ts <= API_V2_TIMESTART:
                    return results
                # else the new start is the api v2 and we now query the normal v2 api
                start_ts = API_V2_TIMESTART

            deserialization_method = partial(self._deserialize_trade, case=case)
            time_step = WEEK_IN_SECONDS
        elif case == KucoinCase.OLD_TRADES:
            deserialization_method = partial(self._deserialize_trade, case=case)
            time_step = WEEK_IN_SECONDS
        elif case in (KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS):
            deserialization_method = partial(
                self._deserialize_asset_movement,
                case=case,
            )
            time_step = MONTH_IN_SECONDS
        else:
            raise AssertionError(f'Unexpected case: {case}')

        call_options = options.copy()
        call_options['startAt'] = Timestamp(max(start_ts, KUCOIN_LAUNCH_TS) * 1000)
        while True:
            current_query_ts = _deserialize_ts(case, call_options['startAt'])
            call_options['endAt'] = Timestamp(
                min(Timestamp(current_query_ts + time_step), end_ts) * 1000,
            )
            logger.debug(
                f'Querying kucoin {case} from {current_query_ts} to {call_options["endAt"]}',
            )
            response = self._api_query(
                case=case,
                options=call_options,
            )
            if response.status_code != HTTPStatus.OK:
                return self._process_unsuccessful_response(
                    response=response,
                    case=case,
                )

            try:
                response_dict = jsonloads_dict(response.text)
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
                if case == KucoinCase.OLD_TRADES and '400100' == response_dict.get('code', ''):
                    if current_query_ts + time_step >= end_ts:
                        break  # end of time range query and last page. We are done.
                    # else update query ts
                    current_query_ts += time_step  # type: ignore
                    continue
                raise RemoteError(msg) from e

            for raw_result in raw_results:
                try:
                    if (
                        case in (KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS) and
                        raw_result['isInner'] is True
                    ):
                        log.debug(f'Found an inner kucoin {case}. Skipping it.')
                        continue

                    result = deserialization_method(raw_result=raw_result)
                except (
                    DeserializationError,
                    KeyError,
                    UnknownAsset,
                    UnprocessableTradePair,
                    UnsupportedAsset,
                ) as e:
                    error_msg = f'Missing key: {str(e)}.' if isinstance(e, KeyError) else str(e)
                    log.error(
                        f'Failed to deserialize a kucoin {case} result',
                        error=error_msg,
                        raw_result=raw_result,
                    )
                    if isinstance(e, (UnknownAsset, UnsupportedAsset)):
                        asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                        error_msg = f'Found {asset_tag} kucoin asset {e.identifier}'

                    self.msg_aggregator.add_error(
                        f'Failed to deserialize a kucoin {case} result. {error_msg}. Ignoring it. '
                        f'Check logs for more details')
                    continue

                results.append(result)  # type: ignore

            is_last_page = total_page in (0, current_page)
            if is_last_page:
                if current_query_ts + time_step >= end_ts:
                    break  # end of time range query and last page. We are done.
                # else update query ts
                current_query_ts += time_step  # type: ignore

            # Update pagination params per endpoint
            # NB: Copying the dict before updating it prevents losing the call args values
            call_options = call_options.copy()
            if not is_last_page:
                call_options['currentPage'] = current_page + 1
            else:
                call_options['currentPage'] = 1
            call_options['startAt'] = Timestamp(current_query_ts * 1000)

        return results

    def _deserialize_accounts_balances(
            self,
            response_dict: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[AssetWithOracles, Balance]:
        """May raise RemoteError
        """
        try:
            accounts_data = response_dict['data']
        except KeyError as e:
            msg = 'Kucoin balances JSON response is missing data key'
            log.error(msg, response_dict)
            raise RemoteError(msg) from e

        assets_balance: DefaultDict[AssetWithOracles, Balance] = defaultdict(Balance)
        for raw_result in accounts_data:
            try:
                amount = deserialize_asset_amount(raw_result['balance'])
                if amount == ZERO:
                    continue

                asset_symbol = raw_result['currency']
            except (KeyError, DeserializationError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key in account: {msg}.'

                log.error(
                    'Failed to deserialize a kucoin balance',
                    error=msg,
                    raw_result=raw_result,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kucoin balance. Ignoring it.',
                )
                continue

            try:
                asset = asset_from_kucoin(asset_symbol)
            except DeserializationError as e:
                log.error(
                    'Unexpected asset symbol in a kucoin balance',
                    error=str(e),
                    raw_result=raw_result,
                )
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kucoin balance. Ignoring it.',
                )
                continue
            except (UnknownAsset, UnsupportedAsset) as e:
                asset_tag = 'unknown' if isinstance(e, UnknownAsset) else 'unsupported'
                self.msg_aggregator.add_warning(
                    f'Found {asset_tag} kucoin asset {e.identifier} while deserializing '
                    f'a balance. Ignoring it.',
                )
                continue
            try:
                usd_price = Inquirer().find_usd_price(asset=asset)
            except RemoteError:
                self.msg_aggregator.add_error(
                    f'Failed to deserialize a kucoin balance after failing to '
                    f'request the USD price of {asset.identifier}. Ignoring it.',
                )
                continue

            assets_balance[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return dict(assets_balance)

    @staticmethod
    def _deserialize_asset_movement(
            raw_result: Dict[str, Any],
            case: Literal[KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS],
    ) -> AssetMovement:
        """Process an asset movement result and deserialize it

        May raise:
        - DeserializationError
        - UnknownAsset
        - UnsupportedAsset
        """
        if case == KucoinCase.DEPOSITS:
            category = AssetMovementCategory.DEPOSIT
        elif case == KucoinCase.WITHDRAWALS:
            category = AssetMovementCategory.WITHDRAWAL
        else:
            raise AssertionError(f'Unexpected case: {case}')

        try:
            timestamp_ms = deserialize_timestamp(raw_result['createdAt'])
            timestamp = Timestamp(int(timestamp_ms / 1000))
            address = raw_result['address']
            # The transaction id can have an @ which we should just get rid of
            transaction_id = raw_result['walletTxId'].split('@')[0]
            amount = deserialize_asset_amount(raw_result['amount'])
            fee = deserialize_fee(raw_result['fee'])
            fee_currency_symbol = raw_result['currency']
            link_id = raw_result.get('id', '')  # NB: id only exists for withdrawals
        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        fee_asset = asset_from_kucoin(fee_currency_symbol)

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
        return asset_movement

    @staticmethod
    def _deserialize_trade(
            raw_result: Dict[str, Any],
            case: Literal[KucoinCase.TRADES, KucoinCase.OLD_TRADES],
    ) -> Trade:
        """Process a trade result and deserialize it

        For the old v1 trades look here:
        https://github.com/ccxt/ccxt/blob/ed5f6f424f7777db03022df8dcc6553b3230006b/python/ccxt/kucoin.py#L1181

        May raise:
        - DeserializationError
        - UnknownAsset
        - UnprocessableTradePair
        - UnsupportedAsset
        """
        try:
            timestamp = deserialize_timestamp(raw_result['createdAt'])
            trade_type = TradeType.BUY if raw_result['side'] == 'buy' else TradeType.SELL
            # amount_key = 'size' if case == KucoinCase.TRADES else 'amount'
            # amount = deserialize_asset_amount(raw_result['size'])
            fee = deserialize_fee(raw_result['fee'])
            trade_pair_symbol = raw_result['symbol']
            base_asset, quote_asset = deserialize_trade_pair(trade_pair_symbol)
            if case == KucoinCase.TRADES:
                fee_currency_symbol = raw_result['feeCurrency']
                fee_currency = asset_from_kucoin(fee_currency_symbol)
                amount = deserialize_asset_amount(raw_result['size'])
                rate = deserialize_price(raw_result['price'])
                # new trades have the timestamp in ms
                timestamp = Timestamp(int(timestamp / 1000))
                trade_id = raw_result['tradeId']
            else:  # old v1 trades
                amount = deserialize_asset_amount(raw_result['amount'])
                fee_currency = quote_asset if trade_type == TradeType.SELL else base_asset
                rate = deserialize_price(raw_result['dealPrice'])
                trade_id = raw_result['id']

        except KeyError as e:
            raise DeserializationError(f'Missing key: {str(e)}.') from e

        trade = Trade(
            timestamp=timestamp,
            location=Location.KUCOIN,
            base_asset=base_asset,
            quote_asset=quote_asset,
            trade_type=trade_type,
            amount=amount,
            rate=rate,
            fee=fee,
            fee_currency=fee_currency,
            link=str(trade_id),
            notes='',
        )
        return trade

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal[KucoinCase.API_KEY],
    ) -> Tuple[bool, str]:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal[KucoinCase.BALANCES],
    ) -> ExchangeQueryBalances:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal[KucoinCase.TRADES, KucoinCase.OLD_TRADES],
    ) -> List[Trade]:
        ...

    @overload
    def _process_unsuccessful_response(  # pylint: disable=no-self-use
            self,
            response: Response,
            case: Literal[KucoinCase.DEPOSITS, KucoinCase.WITHDRAWALS],
    ) -> List[AssetMovement]:
        ...

    def _process_unsuccessful_response(
            self,
            response: Response,
            case: Literal[
                KucoinCase.API_KEY,
                KucoinCase.BALANCES,
                KucoinCase.TRADES,
                KucoinCase.OLD_TRADES,
                KucoinCase.DEPOSITS,
                KucoinCase.WITHDRAWALS,
            ],
    ) -> Union[
        List,
        Tuple[bool, str],
        ExchangeQueryBalances,
    ]:
        """Process unsuccessful responses

        May raise RemoteError
        """
        try:
            response_dict = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            msg = f'Kucoin {case} returned an invalid JSON response: {response.text}.'
            log.error(msg)

            if case in (KucoinCase.API_KEY, KucoinCase.BALANCES):
                return False, msg
            if case in PAGINATED_CASES:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Kucoin {case}: {msg}',
                )
                return []

            raise AssertionError(f'Unexpected case: {case}') from e

        try:
            error_code = response_dict.get('code', None)
            if error_code is not None:
                error_code = deserialize_int_from_str(error_code, 'kucoin response parsing')
        except DeserializationError as e:
            raise RemoteError(f'Could not read Kucoin error code {error_code} as an int') from e

        if error_code in API_KEY_ERROR_CODE_ACTION:
            msg = API_KEY_ERROR_CODE_ACTION[error_code]
        else:
            reason = response_dict.get('msg', None) or response.text
            msg = (
                f'Kucoin query responded with error status code: {response.status_code} '
                f'and text: {reason}.'
            )
            log.error(msg)

        if case in (KucoinCase.BALANCES, KucoinCase.API_KEY):
            return False, msg
        if case in PAGINATED_CASES:
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

        May raise RemoteError
        """
        accounts_response = self._api_query(KucoinCase.BALANCES)
        if accounts_response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=accounts_response,
                case=KucoinCase.BALANCES,
            )
            return result, msg

        try:
            response_dict = jsonloads_dict(accounts_response.text)
        except JSONDecodeError as e:
            msg = f'Kucoin balances returned an invalid JSON response: {accounts_response.text}.'
            log.error(msg)
            raise RemoteError(msg) from e

        account_balances = self._deserialize_accounts_balances(response_dict=response_dict)
        return account_balances, ''

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Return the account deposits and withdrawals

        May raise RemoteError
        """
        options = {
            'currentPage': 1,
            'pageSize': API_PAGE_SIZE_LIMIT,
            'status': 'SUCCESS',
        }
        asset_movements: List[AssetMovement] = []
        deposits = self._api_query_paginated(
            options=options.copy(),
            case=KucoinCase.DEPOSITS,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        asset_movements.extend(deposits)
        withdrawals = self._api_query_paginated(
            options=options.copy(),
            case=KucoinCase.WITHDRAWALS,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        asset_movements.extend(withdrawals)

        return asset_movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        """Return the account trades

        May raise RemoteError
        """
        options = {
            'currentPage': 1,
            'pageSize': API_PAGE_SIZE_LIMIT,
            'tradeType': 'TRADE',  # discarded MARGIN_TRADE
            'status': 'done',
        }
        trades: List[Trade] = self._api_query_paginated(
            options=options,
            case=KucoinCase.TRADES,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        return trades, (start_ts, end_ts)

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the KuCoin API key is good for usage in rotki

        May raise RemoteError
        """
        response = self._api_query(KucoinCase.BALANCES)

        if response.status_code != HTTPStatus.OK:
            result, msg = self._process_unsuccessful_response(
                response=response,
                case=KucoinCase.API_KEY,
            )
            return result, msg

        return True, ''

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for kucoin

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for kucoin
