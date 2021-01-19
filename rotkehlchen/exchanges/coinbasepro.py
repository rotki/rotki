import binascii
import csv
import hashlib
import hmac
import json
import logging
import os
import time
from base64 import b64decode, b64encode
from collections import defaultdict
from http import HTTPStatus
from json.decoder import JSONDecodeError
from tempfile import TemporaryDirectory
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

import gevent
import requests
from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_date,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, Fee, Location, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_now
from rotkehlchen.utils.serialization import rlk_jsonloads_dict, rlk_jsonloads_list

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


SECS_TO_WAIT_FOR_REPORT = 300
MINS_TO_WAIT_FOR_REPORT = SECS_TO_WAIT_FOR_REPORT / 60


def coinbasepro_to_worldpair(product: str) -> TradePair:
    """Turns a coinbasepro product into our trade pair format

    - Can raise UnprocessableTradePair if product is in unexpected format
    - Case raise UnknownAsset if any of the pair assets are not known to Rotki
    """
    parts = product.split('-')
    if len(parts) != 2:
        raise UnprocessableTradePair(product)

    base_asset = Asset(parts[0])
    quote_asset = Asset(parts[1])

    return TradePair(f'{base_asset.identifier}_{quote_asset.identifier}')


class CoinbaseProPermissionError(Exception):
    pass


class Coinbasepro(ExchangeInterface):  # lgtm[py/missing-call-to-init]

    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            passphrase: str,
    ):
        super().__init__('coinbasepro', api_key, secret, database)
        self.base_uri = 'https://api.pro.coinbase.com'
        self.msg_aggregator = msg_aggregator

        self.session.headers.update({
            'Content-Type': 'Application/JSON',
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': passphrase,
        })

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Coinbase Pro API key is good for usage in Rotki

        Makes sure that the following permissions are given to the key:
        - View
        """
        try:
            self._api_query('accounts')
        except CoinbaseProPermissionError:
            msg = (
                'Provided Coinbase Pro API key needs to have "View" permission activated. '
                'Please log into your coinbase account and create a key with '
                'the required permissions.'
            )
            return False, msg
        except RemoteError as e:
            error = str(e)
            if 'Invalid Passphrase' in error:
                msg = (
                    'The passphrase for the given API key does not match. Please '
                    'create a key with the preset passphrase "rotki"'
                )
                return False, msg

            return False, error

        return True, ''

    @overload  # noqa: F811
    def _api_query(  # pylint: disable=no-self-use
            self,
            endpoint: Literal['accounts', 'products'],
            request_method: Literal['GET'] = 'GET',
            options: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        ...

    @overload  # noqa: F811
    def _api_query(  # noqa: F811 pylint: disable=no-self-use
            self,
            endpoint: Literal['reports'],
            request_method: Literal['GET', 'POST'] = 'GET',
            options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ...

    @overload  # noqa: F811
    def _api_query(  # noqa: F811 pylint: disable=no-self-use
            self,
            endpoint: str,
            request_method: Literal['GET', 'POST'] = 'GET',
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[List[Any], Dict[str, Any]]:
        ...

    def _api_query(  # noqa: F811
            self,
            endpoint: str,
            request_method: Literal['GET', 'POST'] = 'GET',
            options: Optional[Dict[str, Any]] = None,
    ) -> Union[List[Any], Dict[str, Any]]:
        """Performs a coinbase PRO API Query for endpoint

        You can optionally provide extra arguments to the endpoint via the options argument.

        Raises RemoteError if something went wrong with connecting or reading from the exchange
        Raises CoinbaseProPermissionError if the API Key does not have sufficient
        permissions for the endpoint
        """
        request_url = f'/{endpoint}'

        timestamp = str(int(time.time()))
        if options:
            stringified_options = json.dumps(options, separators=(',', ':'))
        else:
            stringified_options = ''
            options = {}
        message = timestamp + request_method + request_url + stringified_options
        log.debug(
            'Coinbase Pro API query',
            request_method=request_method,
            request_url=request_url,
            options=options,
        )
        if 'products' not in endpoint:
            try:
                signature = hmac.new(
                    b64decode(self.secret),
                    message.encode(),
                    hashlib.sha256,
                ).digest()
            except binascii.Error as e:
                raise RemoteError('Provided API Secret is invalid') from e

            self.session.headers.update({
                'CB-ACCESS-SIGN': b64encode(signature).decode('utf-8'),
                'CB-ACCESS-TIMESTAMP': timestamp,
            })

        retries_left = QUERY_RETRY_TIMES
        while retries_left > 0:
            full_url = self.base_uri + request_url
            try:
                response = self.session.request(
                    request_method.lower(),
                    full_url,
                    data=stringified_options,
                )
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'Coinbase Pro {request_method} query at '
                    f'{full_url} connection error: {str(e)}',
                ) from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                # Backoff a bit by sleeping. Sleep more, the more retries have been made
                gevent.sleep(QUERY_RETRY_TIMES / retries_left)
                retries_left -= 1
            else:
                # get out of the retry loop, we did not get 429 complaint
                break

        json_ret: Union[List[Any], Dict[str, Any]]
        if response.status_code == HTTPStatus.BAD_REQUEST:
            json_ret = rlk_jsonloads_dict(response.text)
            if json_ret['message'] == 'invalid signature':
                raise CoinbaseProPermissionError(
                    f'While doing {request_method} at {endpoint} endpoint the API secret '
                    f'created an invalid signature.',
                )
            # else do nothing and a generic remote error will be thrown below

        elif response.status_code == HTTPStatus.FORBIDDEN:
            raise CoinbaseProPermissionError(
                f'API key does not have permission for {endpoint}',
            )

        if response.status_code != HTTPStatus.OK:
            raise RemoteError(
                f'Coinbase Pro {request_method} query at {full_url} responded with error '
                f'status code: {response.status_code} and text: {response.text}',
            )

        loading_function: Union[Callable[[str], Dict[str, Any]], Callable[[str], List[Any]]]
        if any(x in endpoint for x in ('accounts', 'products')):
            loading_function = rlk_jsonloads_list
        else:
            loading_function = rlk_jsonloads_dict

        try:
            json_ret = loading_function(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'Coinbase Pro {request_method} query at {full_url} '
                f'returned invalid JSON response: {response.text}',
            ) from e

        return json_ret

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            accounts = self._api_query('accounts')
        except (CoinbaseProPermissionError, RemoteError) as e:
            msg = f'Coinbase Pro API request failed. {str(e)}'
            log.error(msg)
            return None, msg

        assets_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for account in accounts:
            try:
                amount = deserialize_asset_amount(account['balance'])
                # ignore empty balances. Coinbase returns zero balances for everything
                # a user does not own
                if amount == ZERO:
                    continue

                asset = asset_from_coinbase(account['currency'])
                try:
                    usd_price = Inquirer().find_usd_price(asset=asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing coinbasepro balance result due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                assets_balance[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase pro balance result with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found coinbase pro balance result with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a coinbase pro account balance. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a coinbase pro account balance',
                    account_balance=account,
                    error=msg,
                )
                continue

        return dict(assets_balance), ''

    def _get_products_ids(self) -> List[str]:
        """Gets a list of all product ids (markets) offered by coinbase PRO

        - Raises the same exceptions as _api_query()
        - Can raise KeyError if the API does not return the expected response format.
        """
        products = self._api_query('products', request_method='GET')
        return [product['id'] for product in products]

    def _get_account_ids(self) -> List[str]:
        """Gets a list of all account ids

        - Raises the same exceptions as _api_query()
        - Can raise KeyError if the API does not return the expected response format.
        """
        accounts = self._api_query('accounts')
        return [account['id'] for account in accounts]

    def _read_asset_movements(self, filepath: str) -> List[AssetMovement]:
        """Reads a csv account type report and extracts the AssetMovements"""
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            movements = []
            for row in reader:
                try:
                    if row['type'] in ('withdrawal', 'deposit'):
                        timestamp = deserialize_timestamp_from_date(
                            row['time'],
                            'iso8601',
                            'coinbasepro',
                        )
                        asset = Asset(row['amount/balance unit'])
                        movements.append(AssetMovement(
                            location=Location.COINBASEPRO,
                            category=deserialize_asset_movement_category(row['type']),
                            address=None,  # can't get it from csv data
                            transaction_id=None,  # can't get it from csv data
                            timestamp=timestamp,
                            asset=asset,
                            amount=deserialize_asset_amount_force_positive(row['amount']),
                            fee_asset=asset,
                            # I don't see any fee in deposit withdrawals in coinbasepro
                            fee=Fee(ZERO),
                            link=str(row['transfer id']),
                        ))
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown Coinbasepro asset {e.asset_name}. '
                        f'Ignoring its deposit/withdrawal.',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        'Failed to deserialize a Coinbasepro deposit/withdrawal. '
                        'Check logs for details. Ignoring it.',
                    )
                    log.error(
                        'Error processing a coinbasepro  deposit/withdrawal.',
                        raw_asset_movement=row,
                        error=msg,
                    )
                    continue

        return movements

    def _read_trades(self, filepath: str) -> List[Trade]:
        """Reads a csv fill type report and extracts the Trades"""
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            trades = []
            for row in reader:
                try:
                    timestamp = deserialize_timestamp_from_date(
                        row['created at'],
                        'iso8601',
                        'coinbasepro',
                    )
                    trades.append(Trade(
                        timestamp=timestamp,
                        location=Location.COINBASEPRO,
                        pair=coinbasepro_to_worldpair(row['product']),
                        trade_type=deserialize_trade_type(row['side']),
                        amount=deserialize_asset_amount(row['size']),
                        rate=deserialize_price(row['price']),
                        fee=deserialize_fee(row['fee']),
                        fee_currency=Asset(row['price/fee/total unit']),
                        link=row['trade id'],
                        notes='',
                    ))
                except UnprocessableTradePair as e:
                    self.msg_aggregator.add_warning(
                        f'Found unprocessable Coinbasepro pair {e.pair}. Ignoring the trade.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown Coinbasepro asset {e.asset_name}. '
                        f'Ignoring the trade.',
                    )
                    continue
                except (DeserializationError, KeyError) as e:
                    msg = str(e)
                    if isinstance(e, KeyError):
                        msg = f'Missing key entry for {msg}.'
                    self.msg_aggregator.add_error(
                        'Failed to deserialize a coinbasepro trade. '
                        'Check logs for details. Ignoring it.',
                    )
                    log.error(
                        'Error processing a coinbasepro trade.',
                        raw_trade=row,
                        error=msg,
                    )
                    continue

        return trades

    def _generate_reports(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            report_type: Literal['fills', 'account'],
            tempdir: str,
    ) -> List[str]:
        """
        Generates all the reports to get historical data from coinbase.

        https://docs.pro.coinbase.com/#reports
        There are 2 type of reports.
        1. Fill reports which are per product id (market)
        2. Account reports which are per account id

        The fill reports have the following data format:
        portfolio,trade id,product,side,created at,size,size unit,price,fee,
        total,price/fee/total unit

        The account reports have the following data format:
        portfolio,type,time,amount,balance,amount/balance unit,transfer id,trade id,order id

        Returns a list of filepaths where the reports were written.

        - Raises the same exceptions as _api_query()
        - Can raise KeyError if the API does not return the expected response format.
        """
        start_date = timestamp_to_iso8601(start_ts)
        end_date = timestamp_to_iso8601(end_ts)

        if report_type == 'fills':
            account_or_product_ids = self._get_products_ids()
            identifier_key = 'product_id'
        else:
            account_or_product_ids = self._get_account_ids()
            identifier_key = 'account_id'

        report_ids = []
        options = {
            'type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'format': 'csv',
            # The only way to disable emailing the report link is to give an invalid link
            'email': 'some@invalidemail.com',
        }
        for identifier in account_or_product_ids:
            options[identifier_key] = identifier
            post_result = self._api_query('reports', request_method='POST', options=options)
            report_ids.append(post_result['id'])

        # At this point all reports must have been queued for creation at the server
        # Now wait until they are ready and pull them one by one
        report_paths = []
        last_change_ts = ts_now()
        while True:
            finished_ids_indices = []
            for idx, report_id in enumerate(report_ids):
                get_result = self._api_query(f'reports/{report_id}', request_method='GET')
                # Have to add assert here for mypy since the endpoint string is
                # a variable string and can't be overloaded and type checked
                assert isinstance(get_result, dict)
                if get_result['status'] != 'ready':
                    continue
                # a report is ready here so let's reset the timer
                last_change_ts = ts_now()
                file_url = get_result['file_url']
                response = requests.get(file_url)
                length = len(response.content)
                # empty fill reports have length of 95, empty account reports 85
                # So we assume a report of more than 100 chars has data.
                if length > 100:
                    log.debug(f'Got a populated report for id: {report_id}. Writing it to disk')
                    filepath = os.path.join(tempdir, f'report_{report_id}.csv')
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    report_paths.append(filepath)
                else:
                    log.debug(f'Got report for id: {report_id} with length {length}. Skipping it')

                finished_ids_indices.append(idx)

            if ts_now() - last_change_ts > SECS_TO_WAIT_FOR_REPORT:
                raise RemoteError(
                    f'There has been no response from CoinbasePro reports for over '
                    f' {MINS_TO_WAIT_FOR_REPORT} minutes. Bailing out.',
                )

            # Delete the report ids that have been downloaded. Note: reverse order
            # so that we don't mess up the indices
            for idx in reversed(finished_ids_indices):
                del report_ids[idx]

            # When there is no more ids to query break out of the loop
            if len(report_ids) == 0:
                break

        return report_paths

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Queries coinbase pro for asset movements

        1. Generates relevant reports and writes them to a temporary directory
        2. Reads all files from that directory and extracts deposits/withdrawals
        3. Temporary directory is removed
        """
        log.debug('Query coinbasepro asset movements', start_ts=start_ts, end_ts=end_ts)
        movements = []
        with TemporaryDirectory() as tempdir:
            try:
                filepaths = self._generate_reports(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    report_type='account',
                    tempdir=tempdir,
                )
            except CoinbaseProPermissionError as e:
                self.msg_aggregator.add_error(
                    f'Got permission error while querying Coinbasepro for '
                    f'asset movements: {str(e)}',
                )
                return []
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Coinbasepro for '
                    f'asset movements: {str(e)}',
                )
                return []

            for filepath in filepaths:
                movements.extend(self._read_asset_movements(filepath))

        return movements

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Queries coinbase pro for trades

        1. Generates relevant reports and writes them to a temporary directory
        2. Reads all files from that directory and extracts Trades
        3. Temporary directory is removed
        """
        log.debug('Query coinbasepro trade history', start_ts=start_ts, end_ts=end_ts)
        trades = []
        with TemporaryDirectory() as tempdir:
            try:
                filepaths = self._generate_reports(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    report_type='fills',
                    tempdir=tempdir,
                )
            except CoinbaseProPermissionError as e:
                self.msg_aggregator.add_error(
                    f'Got permission error while querying Coinbasepro for trades: {str(e)}',
                )
                return []
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Got remote error while querying Coinbasepro for trades: {str(e)}',
                )
                return []

            for filepath in filepaths:
                trades.extend(self._read_trades(filepath))

        return trades

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for coinbasepro
