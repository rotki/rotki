import hmac
import logging
import time
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Tuple, Union, overload
from urllib.parse import urlencode, quote

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_ftx
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, AssetMovementCategory, Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
INITIAL_BACKOFF_TIME = 2
BACKOFF_LIMIT = 60
PAGINATION_LIMIT = 100

FTX_SUBACCOUNT_DB_SETTING = 'ftx_subaccount'


def trade_from_ftx(raw_trade: Dict[str, Any]) -> Optional[Trade]:
    """Turns an FTX transaction into a rotki Trade.

    May raise:
        - UnknownAsset due to Asset instantiation
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected key
    """
    # In the case of perpetuals and futures this fields can be None
    if raw_trade.get('baseCurrency', None) is None:
        return None
    if raw_trade.get('quoteCurrency', None) is None:
        return None

    timestamp = deserialize_timestamp_from_date(raw_trade['time'], 'iso8601', 'FTX')
    trade_type = deserialize_trade_type(raw_trade['side'])
    base_asset = asset_from_ftx(raw_trade['baseCurrency'])
    quote_asset = asset_from_ftx(raw_trade['quoteCurrency'])
    amount = deserialize_asset_amount(raw_trade['size'])
    rate = deserialize_price(raw_trade['price'])
    fee_currency = asset_from_ftx(raw_trade['feeCurrency'])
    fee = deserialize_fee(raw_trade['fee'])

    return Trade(
        timestamp=timestamp,
        location=Location.FTX,
        base_asset=base_asset,
        quote_asset=quote_asset,
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(raw_trade['id']),
    )


class Ftx(ExchangeInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            ftx_subaccount_name: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            location=Location.FTX,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.apiversion = 'v2'
        self.base_uri = 'https://ftx.com'
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({'FTX-KEY': self.api_key})
        self.subaccount = ftx_subaccount_name
        if self.subaccount is None:
            self.subaccount = self.db.get_ftx_subaccount(self.name)

        if self.subaccount is not None:
            self.session.headers.update({'FTX-SUBACCOUNT': quote(self.subaccount)})

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
            self.session.headers.update({'FTX-KEY': self.api_key})
            subaccount = self.db.get_ftx_subaccount(self.name)
            if subaccount is not None:
                self.session.headers.update({'FTX-SUBACCOUNT': quote(subaccount)})
                self.subaccount = subaccount
            else:
                self.session.headers.pop('FTX-SUBACCOUNT', None)

        return changed

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the FTX API key is good for usage in rotki"""
        endpoint: Literal['account', 'wallet/all_balances']

        if self.subaccount is None:
            endpoint = 'wallet/all_balances'
        else:
            endpoint = 'account'

        try:
            self._api_query(endpoint=endpoint, paginate=False)
        except RemoteError as e:
            error = str(e)
            if 'Not logged in' in error:
                return False, 'Error validating API Keys'
            raise
        return True, ''

    def _make_request(
        self,
        endpoint: str,
        start_time: Optional[Timestamp] = None,
        end_time: Optional[Timestamp] = None,
        limit: int = PAGINATION_LIMIT,
    ) -> Union[List[Dict[str, Any]], Dict[str, List[Any]]]:
        """Performs an FTX API Query for endpoint adding the needed information to
        authenticate user and handling errors.
        This function can raise:
        - RemoteError
        """
        request_verb = "GET"
        backoff = INITIAL_BACKOFF_TIME

        # Use a while loop to retry request if rate limit is reached
        while True:
            request_url = '/api/' + endpoint
            options = {'limit': limit}
            if start_time is not None:
                options['start_time'] = start_time
            if end_time is not None:
                options['end_time'] = end_time

            if len(options) != 0:
                request_url += '?' + urlencode(options)

            timestamp = int(time.time() * 1000)
            signature_payload = f'{timestamp}{request_verb}{request_url}'.encode()
            signature = hmac.new(self.secret, signature_payload, 'sha256').hexdigest()
            log.debug('FTX API query', request_url=request_url)
            self.session.headers.update({
                'FTX-SIGN': signature,
                'FTX-TS': str(timestamp),
            })

            full_url = self.base_uri + request_url
            try:
                response = self.session.get(full_url, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'FTX API request {full_url} failed due to {str(e)}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if backoff < BACKOFF_LIMIT:
                    log.debug(
                        f'FTX rate limit exceeded on request {request_url}. Backing off',
                        seconds=backoff,
                    )
                    gevent.sleep(backoff)
                    backoff = backoff * 2
                    continue
            # We got a result here
            break

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'FTX query {full_url} responded with error status code: '
                f'{response.status_code} and text: {response.text}',
            )

        try:
            json_ret = jsonloads_dict(response.text)
        except JSONDecodeError as e:
            raise RemoteError(f'FTX returned invalid JSON response: {response.text}') from e

        if 'result' not in json_ret:
            raise RemoteError(f'FTX json response does not contain data: {response.text}')

        return json_ret['result']

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['wallet/all_balances'],
            start_time: Optional[Timestamp] = None,
            end_time: Optional[Timestamp] = None,
            limit: int = PAGINATION_LIMIT,
            paginate: bool = True,
    ) -> Dict[str, List[Any]]:
        ...

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['wallet/balances'],
            start_time: Optional[Timestamp] = None,
            end_time: Optional[Timestamp] = None,
            limit: int = PAGINATION_LIMIT,
            paginate: bool = True,
    ) -> List[Dict[str, Any]]:
        ...

    @overload
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['account'],
            start_time: Optional[Timestamp] = None,
            end_time: Optional[Timestamp] = None,
            limit: int = PAGINATION_LIMIT,
            paginate: bool = True,
    ) -> Dict[str, Any]:
        ...

    @overload
    def _api_query(
            self,
            endpoint: Literal[
                'fills',
                'wallet/deposits',
                'wallet/withdrawals',
                'markets',
                'markets/eth/eur/trades',
            ],
            start_time: Optional[Timestamp] = None,
            end_time: Optional[Timestamp] = None,
            limit: int = PAGINATION_LIMIT,
            paginate: bool = True,
    ) -> List[Dict[str, Any]]:
        ...

    def _api_query(
            self,
            endpoint: str,
            start_time: Optional[Timestamp] = None,
            end_time: Optional[Timestamp] = None,
            limit: int = PAGINATION_LIMIT,
            paginate: bool = True,
    ) -> Union[List[Dict[str, Any]], Dict[str, List[Any]], Dict[str, Any]]:
        """Query FTX endpoint and retrieve all available information if pagination
        is requested. In case of paginate being set to False only one request is made.
        Can raise:
        - RemoteError
        """
        if not paginate:
            final_data_no_pag = self._make_request(
                endpoint=endpoint,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )
            return final_data_no_pag

        # If there is pagination we follow the example from the official ftx python example
        # https://github.com/ftexchange/ftx/blob/master/rest/client.py#L163
        # In this case the strategy is a while loop leaving fixed the start_time (lower bound)
        # and decreasing end time (the upper bound) until we fetch all the available information
        new_end_time = end_time
        ids = set()
        final_data: List[Dict[str, Any]] = []
        while True:
            step = self._make_request(
                endpoint=endpoint,
                limit=limit,
                start_time=start_time,
                end_time=new_end_time,
            )

            if not isinstance(step, list):
                raise RemoteError(
                    f'FTX pagination returned something different to a list for route {endpoint} '
                    f'with start_time {start_time} and end_time {end_time}. Result was {step}.',
                )

            # remove possible duplicates
            deduped = [
                r for r in step if
                'id' in r.keys() and r['id'] not in ids
            ]
            ids |= {r['id'] for r in deduped}
            final_data.extend(deduped)

            if len(step) == 0:
                break

            # Avoid deserialization error if there is a bad date
            times = []
            for t in step:
                try:
                    times.append(deserialize_timestamp_from_date(t['time'], 'iso8601', 'ftx'))
                except (DeserializationError, KeyError):
                    continue

            if len(times) != 0:
                new_end_time = min(times)
            else:
                self.msg_aggregator.add_error(
                    f'Error processing FTX trade history. Query step '
                    f'returned invalid entries when trying pagination for endpoint '
                    f'{endpoint} with start_time {start_time}, end_time {end_time} '
                    f'and page limit of {limit}.',
                )
                break

            if len(step) < limit:
                break

        return final_data

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        resp_dict, resp_lst = None, None
        try:
            if self.subaccount is not None:
                resp_lst = self._api_query('wallet/balances', paginate=False)
            else:
                resp_dict = self._api_query('wallet/all_balances', paginate=False)
        except RemoteError as e:
            msg = f'FTX API request failed. Could not reach FTX due to {str(e)}'
            log.error(msg)
            return None, msg

        if resp_dict is not None:
            # flatten the list that maps accounts to balances
            balances: List[Dict[str, Any]] = [x for _, bal in resp_dict.items() for x in bal]
        elif resp_lst is not None:
            # When querying for a subaccount we get a list instead of a dict
            balances = resp_lst

        # extract the balances and aggregate them
        returned_balances: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for balance_info in balances:
            try:
                amount = deserialize_asset_amount(balance_info['total'])
                # ignore empty balances. FTX returns zero for some coins
                if amount == ZERO:
                    continue

                asset = asset_from_ftx(balance_info['coin'])
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing FTX balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                returned_balances[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing an FTX account balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing an FTX balance',
                    error=msg,
                )
                continue
        return dict(returned_balances), ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:

        raw_data = self._api_query('fills', start_time=start_ts, end_time=end_ts)
        log.debug('FTX trades history result', results_num=len(raw_data))

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_ftx(raw_trade)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX trade with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found FTX trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing an FTX trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing an FTX trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue
            if trade:
                trades.append(trade)
        return trades

    def _deserialize_asset_movement(
        self,
        raw_data: Dict[str, Any],
        movement_type: AssetMovementCategory,
    ) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from FTX and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if raw_data['status'] not in ('complete', 'confirmed'):
                return None

            timestamp = deserialize_timestamp_from_date(raw_data['time'], 'iso8601', 'FTX')
            amount = deserialize_asset_amount_force_positive(raw_data['size'])
            asset = asset_from_ftx(raw_data['coin'])
            fee = Fee(ZERO)
            movement_category = movement_type
            if raw_data.get('fee', None) is not None:
                fee = deserialize_fee(raw_data['fee'])
            address = raw_data.get('address', None)
            if isinstance(address, dict):
                address = raw_data['address'].get('address', None)
            transaction_id = raw_data.get('txid', None)

            return AssetMovement(
                location=Location.FTX,
                category=movement_category,
                address=address,
                transaction_id=transaction_id,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                fee=fee,
                link=str(raw_data['id']),
            )
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found FTX deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found FTX deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                'Unexpected data encountered during deserialization of an FTX '
                'asset movement. Check logs for details and open a bug report.',
            )
            log.error(
                'Error processing FTX trade',
                trade=raw_data,
                error=msg,
            )

        return None

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        raw_data_deposits = self._api_query(
            'wallet/deposits',
            start_time=start_ts,
            end_time=end_ts,
        )
        raw_data_withdrawals = self._api_query(
            'wallet/withdrawals',
            start_time=start_ts,
            end_time=end_ts,
        )

        results_num = len(raw_data_deposits) + len(raw_data_withdrawals)
        log.debug('FTX deposits/withdrawals history result', results_num=results_num)

        movements = []
        for raw_deposit in raw_data_deposits:
            movement = self._deserialize_asset_movement(
                raw_data=raw_deposit,
                movement_type=AssetMovementCategory.DEPOSIT,
            )
            if movement:
                movements.append(movement)

        for raw_withdrawal in raw_data_withdrawals:
            movement = self._deserialize_asset_movement(
                raw_data=raw_withdrawal,
                movement_type=AssetMovementCategory.WITHDRAWAL,
            )
            if movement:
                movements.append(movement)

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for FTX
