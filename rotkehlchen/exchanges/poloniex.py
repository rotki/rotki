import base64
import hashlib
import hmac
import json
import logging
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.assets.converters import asset_from_poloniex
from rotkehlchen.constants.assets import A_LEND
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE, QUERY_RETRY_TIMES
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade, TradeType
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp,
    deserialize_timestamp_from_intms,
    get_pair_position_str,
)
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    Fee,
    Location,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


PUBLIC_API_ENDPOINTS = ('/currencies',)


def trade_from_poloniex(poloniex_trade: Dict[str, Any]) -> Trade:
    """Turn a poloniex trade returned from poloniex trade history to our common trade
    history format

    Throws:
        - UnsupportedAsset due to asset_from_poloniex()
        - DeserializationError due to the data being in unexpected format
        - UnprocessableTradePair due to the pair data being in an unexpected format
    """
    try:
        pair = poloniex_trade['symbol']
        trade_type = TradeType.deserialize(poloniex_trade['side'])
        # quantity is the base units of the trade
        amount = deserialize_asset_amount(poloniex_trade['quantity'])
        rate = deserialize_price(poloniex_trade['price'])
        fee = deserialize_fee(poloniex_trade['feeAmount'])
        fee_currency = asset_from_poloniex(poloniex_trade['feeCurrency'])
        base_currency = asset_from_poloniex(get_pair_position_str(pair, 'first'))
        quote_currency = asset_from_poloniex(get_pair_position_str(pair, 'second'))
        timestamp = deserialize_timestamp_from_intms(poloniex_trade['createTime'])
    except KeyError as e:
        raise DeserializationError(
            f'Poloniex trade deserialization error. Missing key entry for {str(e)} in trade dict',
        ) from e

    log.debug(
        'Processing poloniex Trade',
        timestamp=timestamp,
        order_type=trade_type,
        base_currency=base_currency,
        quote_currency=quote_currency,
        amount=amount,
        fee=fee,
        rate=rate,
    )

    return Trade(
        timestamp=timestamp,
        location=Location.POLONIEX,
        # Since in Poloniex the base currency is the cost currency, iow in poloniex
        # for BTC_ETH we buy ETH with BTC and sell ETH for BTC, we need to turn it
        # into the Rotkehlchen way which is following the base/quote approach.
        base_asset=base_currency,
        quote_asset=quote_currency,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(poloniex_trade['id']),
    )


class Poloniex(ExchangeInterface):  # lgtm[py/missing-call-to-init]

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
            location=Location.POLONIEX,
            api_key=api_key,
            secret=secret,
            database=database,
        )

        self.uri = 'https://api.poloniex.com'
        self.session.headers.update({'key': self.api_key})
        self.msg_aggregator = msg_aggregator

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        self.first_connection_made = True

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'key': self.api_key})

        return changed

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self.return_fee_info()
        except RemoteError as e:
            error = str(e)
            if 'Invalid API key' in error:
                return False, 'Provided API Key or secret is invalid'
            # else reraise
            raise
        return True, ''

    def api_query_dict(self, command: str, req: Optional[Dict] = None) -> Dict:
        result = self._api_query(command, req)
        if not isinstance(result, Dict):
            raise RemoteError(
                f'Poloniex query for {command} did not return a dict result. Result: {result}',
            )
        return result

    def api_query_list(self, command: str, req: Optional[Dict] = None) -> List:
        result = self._api_query(command, req)
        if not isinstance(result, List):
            raise RemoteError(
                f'Poloniex query for {command} did not return a list result. Result: {result}',
            )
        return result

    def _create_sign(
            self,
            timestamp: TimestampMS,
            params: Dict[str, Any],
            method: Literal['GET'],
            path: str,
    ) -> str:
        """Method taken from here:
         https://github.com/poloniex/polo-spot-sdk/tree/BRANCH_SANDBOX/signature_demo
        """
        if method == 'GET':
            params.update({'signTimestamp': timestamp})
            sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
            encode_params = urlencode(sorted_params)
            del params['signTimestamp']
        else:
            request_body = json.dumps(params)  # type: ignore
            encode_params = 'requestBody={}&signTimestamp={}'.format(
                request_body, timestamp,
            )
        sign_params_first = [method, path, encode_params]
        sign_params_second = '\n'.join(sign_params_first)
        sign_params = sign_params_second.encode(encoding='UTF8')
        digest = hmac.new(self.secret, sign_params, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(digest)
        return signature.decode()

    def _single_query(self, path: str, req: Dict[str, Any]) -> Optional[requests.Response]:
        """A single api query for poloniex

        Returns the response if all went well or None if a recoverable poloniex
        error occured such as a 504.

        Can raise:
         - RemoteError if there is a problem with the response
         - ConnectionError if there is a problem connecting to poloniex.
        """
        if path in PUBLIC_API_ENDPOINTS:
            log.debug(f'Querying poloniex for {path}')
            response = self.session.get(self.uri + path, timeout=DEFAULT_TIMEOUT_TUPLE)
        else:
            timestamp = ts_now_in_ms()
            sign = self._create_sign(timestamp=timestamp, params=req, method='GET', path=path)
            self.session.headers.update({
                'signTimestamp': str(timestamp),
                'signature': sign,
            })
            params = urlencode(req)
            if params == '':
                url = '{host}{path}'.format(host=self.uri, path=path)
            else:
                url = '{host}{path}?{params}'.format(host=self.uri, path=path, params=params)
            response = self.session.get(url, params={}, timeout=DEFAULT_TIMEOUT_TUPLE)

        if response.status_code == 504:
            # backoff and repeat
            return None
        if response.status_code != 200:
            raise RemoteError(
                f'Poloniex query responded with error status code: {response.status_code}'
                f' and text: {response.text}',
            )

        # else all is good
        return response

    def _api_query(self, command: str, req: Optional[Dict] = None) -> Union[Dict, List]:
        """An api query to poloniex. May make multiple requests

        Can raise:
         - RemoteError if there is a problem reaching poloniex or with the returned response
        """
        if req is None:
            req = {}
        log.debug(
            'Poloniex API query',
            command=command,
            post_data=req,
        )

        tries = QUERY_RETRY_TIMES
        while tries >= 0:
            try:
                response = self._single_query(command, req)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'Poloniex API request failed due to {str(e)}') from e

            if response is None:
                if tries >= 1:
                    backoff_seconds = 20 / tries
                    log.debug(
                        f'Got a recoverable poloniex error. '
                        f'Backing off for {backoff_seconds}',
                    )
                    gevent.sleep(backoff_seconds)
                    tries -= 1
                    continue
            else:
                break

        if response is None:
            raise RemoteError(
                f'Got a recoverable poloniex error and did not manage to get a '
                f'request through even after {QUERY_RETRY_TIMES} '
                f'incremental backoff retries',
            )

        result: Union[Dict, List]
        try:
            result = response.json()
        except JSONDecodeError as e:
            raise RemoteError(f'Poloniex returned invalid JSON response: {response.text}') from e

        if isinstance(result, dict) and 'error' in result:
            raise RemoteError(
                'Poloniex query for "{}" returned error: {}'.format(
                    command,
                    result['error'],
                ))

        return result

    def return_fee_info(self) -> Dict:
        response = self.api_query_dict('/feeinfo')
        return response

    def return_trade_history(
            self,
            start: Timestamp,
            end: Timestamp,
    ) -> List[Dict[str, Any]]:
        """Returns poloniex trade history"""
        limit = 100
        data: List[Dict[str, Any]] = []
        start_ms = start * 1000
        end_ms = end * 1000
        while True:
            new_data = self.api_query_list('/trades', {
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': limit,
            })
            results_length = len(new_data)
            if data == [] and results_length < limit:
                return new_data  # simple case - only one query needed

            latest_ts_ms = start_ms
            # add results to data and prepare for next query
            existing_ids = {x['id'] for x in data}
            for trade in new_data:
                try:
                    timestamp_ms = trade['createTime']
                    latest_ts_ms = max(latest_ts_ms, timestamp_ms)
                    # since we query again from last ts seen make sure no duplicates make it in
                    if trade['id'] not in existing_ids:
                        data.append(trade)
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_warning(
                        'Error deserializing a poloniex trade. Check the logs for details',
                    )
                    log.error(
                        'Error deserializing poloniex trade',
                        trade=trade,
                        error=msg,
                    )
                    continue

            if results_length < limit:
                break  # last query has less than limit. We are done.

            # otherwise we query again from the last ts seen in the last result
            start_ms = latest_ts_ms
            continue

        return data

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            resp = self.api_query_list('/accounts/balances')
        except RemoteError as e:
            msg = (
                'Poloniex API request failed. Could not reach poloniex due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        assets_balance: Dict[AssetWithOracles, Balance] = {}
        for account_info in resp:
            try:
                balances = account_info['balances']
            except KeyError:
                self.msg_aggregator.add_error('Could not find balances key in the balances response')  # noqa: E501
                continue

            for balance_entry in balances:
                try:
                    available = deserialize_asset_amount(balance_entry['available'])
                    on_orders = deserialize_asset_amount(balance_entry['hold'])
                    poloniex_asset = balance_entry['currency']
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        f'Could not deserialize amount from poloniex due to '
                        f'{msg}. Ignoring its balance query.',
                    )
                    continue

                if available != ZERO or on_orders != ZERO:
                    try:
                        asset = asset_from_poloniex(poloniex_asset)
                    except UnsupportedAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found unsupported poloniex asset {e.identifier}. '
                            f'Ignoring its balance query.',
                        )
                        continue
                    except UnknownAsset as e:
                        self.msg_aggregator.add_warning(
                            f'Found unknown poloniex asset {e.identifier}. '
                            f'Ignoring its balance query.',
                        )
                        continue
                    except DeserializationError:
                        log.error(
                            f'Unexpected poloniex asset type. Expected string '
                            f' but got {type(poloniex_asset)}',
                        )
                        self.msg_aggregator.add_error(
                            'Found poloniex asset entry with non-string type. '
                            'Ignoring its balance query.',
                        )
                        continue

                    if asset == A_LEND:  # poloniex mistakenly returns LEND balances
                        continue  # https://github.com/rotki/rotki/issues/2530

                    try:
                        usd_price = Inquirer().find_usd_price(asset=asset)
                    except RemoteError as e:
                        self.msg_aggregator.add_error(
                            f'Error processing poloniex balance entry due to inability to '
                            f'query USD price: {str(e)}. Skipping balance entry',
                        )
                        continue

                    amount = available + on_orders
                    usd_value = amount * usd_price
                    assets_balance[asset] = Balance(
                        amount=amount,
                        usd_value=usd_value,
                    )
                    log.debug(
                        'Poloniex balance query',
                        currency=asset,
                        amount=amount,
                        usd_value=usd_value,
                    )

        return assets_balance, ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        raw_data = self.return_trade_history(
            start=start_ts,
            end=end_ts,
        )
        log.debug('Poloniex trade history query', results_num=len(raw_data))
        our_trades = []
        for trade in raw_data:
            account_type = trade.get('accountType', None)
            try:
                if account_type == 'SPOT':
                    timestamp = deserialize_timestamp_from_intms(trade['createTime'])
                    if timestamp < start_ts or timestamp > end_ts:
                        continue
                    our_trades.append(trade_from_poloniex(trade))
                else:
                    log.warning(
                        f'Error deserializing a poloniex trade. Unknown trade '
                        f'accountType {account_type} found.',
                    )
                    continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found poloniex trade with unsupported asset'
                    f' {e.identifier}. Ignoring it.',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found poloniex trade with unknown asset'
                    f' {e.identifier}. Ignoring it.',
                )
                continue
            except (UnprocessableTradePair, DeserializationError) as e:
                self.msg_aggregator.add_error(
                    'Error deserializing a poloniex trade. Check the logs '
                    'and open a bug report.',
                )
                log.error(
                    'Error deserializing poloniex trade',
                    trade=trade,
                    error=str(e),
                )
                continue

        return our_trades, (start_ts, end_ts)

    def _deserialize_asset_movement(
            self,
            movement_type: AssetMovementCategory,
            movement_data: Dict[str, Any],
    ) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from polo and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if movement_type == AssetMovementCategory.DEPOSIT:
                fee = Fee(ZERO)
                uid_key = 'depositNumber'
                transaction_id = get_key_if_has_val(movement_data, 'txid')
            else:
                fee = deserialize_fee(movement_data['fee'])
                uid_key = 'withdrawalRequestsId'
                split = movement_data['status'].split(':')
                if len(split) != 2:
                    transaction_id = None
                else:
                    transaction_id = split[1].lstrip()
                    if transaction_id == '':
                        transaction_id = None

            asset = asset_from_poloniex(movement_data['currency'])
            return AssetMovement(
                location=Location.POLONIEX,
                category=movement_type,
                address=deserialize_asset_movement_address(movement_data, 'address', asset),
                transaction_id=transaction_id,
                timestamp=deserialize_timestamp(movement_data['timestamp']),
                asset=asset,
                amount=deserialize_asset_amount_force_positive(movement_data['amount']),
                fee_asset=asset,
                fee=fee,
                link=str(movement_data[uid_key]),
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(movement_type)} of unsupported poloniex asset '
                f'{e.identifier}. Ignoring it.',
            )
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(movement_type)} of unknown poloniex asset '
                f'{e.identifier}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of a poloniex '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                f'Unexpected data encountered during deserialization of poloniex '
                f'{str(movement_type)}: {movement_data}. Error was: {msg}',
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        result = self.api_query_dict(
            '/wallets/activity',
            {'start': start_ts, 'end': end_ts},
        )
        log.debug(
            'Poloniex deposits/withdrawal query',
            results_num=len(result['withdrawals']) + len(result['deposits']),
        )

        movements = []
        for withdrawal in result['withdrawals']:
            asset_movement = self._deserialize_asset_movement(
                movement_type=AssetMovementCategory.WITHDRAWAL,
                movement_data=withdrawal,
            )
            if asset_movement:
                movements.append(asset_movement)

        for deposit in result['deposits']:
            asset_movement = self._deserialize_asset_movement(
                movement_type=AssetMovementCategory.DEPOSIT,
                movement_data=deposit,
            )
            if asset_movement:
                movements.append(asset_movement)

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for poloniex

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for poloniex
