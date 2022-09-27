import hashlib
import hmac
import json
import logging
from collections import defaultdict
from json.decoder import JSONDecodeError
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlencode

import gevent
import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.db.constants import BINANCE_MARKETS_KEY
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    BinancePair,
    MarginPosition,
    Trade,
    TradeType,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.exchanges.utils import (
    deserialize_asset_movement_address,
    get_key_if_has_val,
    query_binance_exchange_pairs,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_fee,
    deserialize_timestamp_from_date,
    deserialize_timestamp_from_intms,
)
from rotkehlchen.types import ApiKey, ApiSecret, AssetMovementCategory, Fee, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now_in_ms
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Binance launched at 2017-07-14T04:00:00Z (12:00 GMT+8, Beijing Time)
# https://www.binance.com/en/support/articles/115000599831-Binance-Exchange-Launched-Date-Set
BINANCE_LAUNCH_TS = Timestamp(1500001200)
API_TIME_INTERVAL_CONSTRAINT_TS = Timestamp(7776000)  # 90 days

V3_METHODS = (
    'account',
    'myTrades',
    'openOrders',
    'exchangeInfo',
    'time',
)
PUBLIC_METHODS = ('exchangeInfo', 'time')

RETRY_AFTER_LIMIT = 60
# Binance api error codes we check for (all below apis seem to have the same)
# https://binance-docs.github.io/apidocs/spot/en/#error-codes-2
# https://binance-docs.github.io/apidocs/futures/en/#error-codes-2
# https://binance-docs.github.io/apidocs/delivery/en/#error-codes-2
REJECTED_MBX_KEY = -2015


BINANCE_API_TYPE = Literal['api', 'sapi', 'dapi', 'fapi']

BINANCE_BASE_URL = 'binance.com/'
BINANCEUS_BASE_URL = 'binance.us/'


class BinancePermissionError(RemoteError):
    """Exception raised when a binance permission problem is detected

    Example is when there is no margin account to query or insufficient api key permissions."""


def trade_from_binance(
        binance_trade: Dict,
        binance_symbols_to_pair: Dict[str, BinancePair],
        location: Location,
) -> Trade:
    """Turn a binance trade returned from trade history to our common trade
    history format

    From the official binance api docs (01/09/18):
    https://github.com/binance-exchange/binance-official-api-docs/blob/62ff32d27bb32d9cc74d63d547c286bb3c9707ef/rest-api.md#terminology

    base asset refers to the asset that is the quantity of a symbol.
    quote asset refers to the asset that is the price of a symbol.

    Throws:
        - UnsupportedAsset due to asset_from_binance
        - DeserializationError due to unexpected format of dict entries
        - KeyError due to dict entries missing an expected entry
    """
    amount = deserialize_asset_amount(binance_trade['qty'])
    rate = deserialize_price(binance_trade['price'])
    if binance_trade['symbol'] not in binance_symbols_to_pair:
        raise DeserializationError(
            f'Error reading a {str(location)} trade. Could not find '
            f'{binance_trade["symbol"]} in binance_symbols_to_pair',
        )

    binance_pair = binance_symbols_to_pair[binance_trade['symbol']]
    timestamp = deserialize_timestamp_from_intms(binance_trade['time'])

    base_asset = binance_pair.base_asset
    quote_asset = binance_pair.quote_asset

    if binance_trade['isBuyer']:
        order_type = TradeType.BUY
        # e.g. in RDNETH we buy RDN by paying ETH
    else:
        order_type = TradeType.SELL

    fee_currency = asset_from_binance(binance_trade['commissionAsset'])
    fee = deserialize_fee(binance_trade['commission'])

    log.debug(
        f'Processing {str(location)} Trade',
        amount=amount,
        rate=rate,
        timestamp=timestamp,
        pair=binance_trade['symbol'],
        base_asset=base_asset,
        quote=quote_asset,
        order_type=order_type,
        commision_asset=binance_trade['commissionAsset'],
        fee=fee,
    )
    return Trade(
        timestamp=timestamp,
        location=location,
        base_asset=base_asset,
        quote_asset=quote_asset,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=fee_currency,
        link=str(binance_trade['id']),
    )


class Binance(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    """This class supports:
      - Binance: when instantiated with default uri, equals BINANCE_BASE_URL.
      - Binance US: when instantiated with uri equals BINANCEUS_BASE_URL.

    Binance exchange api docs:
    https://github.com/binance-exchange/binance-official-api-docs/

    Binance US exchange api docs:
    https://github.com/binance-us/binance-official-api-docs

    An unofficial python binance package:
    https://github.com/binance-exchange/python-binance/
    """
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            uri: str = BINANCE_BASE_URL,
            binance_selected_trade_pairs: Optional[List[str]] = None,  # noqa: N803
    ):
        exchange_location = Location.BINANCE
        if uri == BINANCEUS_BASE_URL:
            exchange_location = Location.BINANCEUS

        super().__init__(
            name=name,
            location=exchange_location,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.uri = uri
        self.session.headers.update({
            'Accept': 'application/json',
            'X-MBX-APIKEY': self.api_key,
        })
        self.msg_aggregator = msg_aggregator
        self.offset_ms = 0
        self.selected_pairs = binance_selected_trade_pairs

    def first_connection(self) -> None:
        if self.first_connection_made:
            return

        # If it's the first time, populate the binance pair trade symbols
        # We know exchangeInfo returns a dict
        try:
            self._symbols_to_pair = query_binance_exchange_pairs(location=self.location)
        except InputError as e:
            self.msg_aggregator.add_error(
                f'Binance exchange couldnt be properly initialized. '
                f'Missing the exchange markets. {str(e)}',
            )
            self._symbols_to_pair = {}

        server_time = self.api_query_dict('api', 'time')
        self.offset_ms = server_time['serverTime'] - ts_now_in_ms()

        self.first_connection_made = True

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'X-MBX-APIKEY': api_key})
        return changed

    def edit_exchange(
            self,
            name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            **kwargs: Any,
    ) -> Tuple[bool, str]:
        success, msg = super().edit_exchange(
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            **kwargs,
        )
        if success is False:
            return success, msg

        binance_markets = kwargs.get(BINANCE_MARKETS_KEY)
        if binance_markets is None:
            return success, msg

        # here we can finally update the account type
        self.selected_pairs = binance_markets
        return True, ''

    @property
    def symbols_to_pair(self) -> Dict[str, BinancePair]:
        """Returns binance symbols to pair if in memory otherwise queries binance"""
        self.first_connection()
        return self._symbols_to_pair

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            # We know account endpoint returns a dict
            self.api_query_dict('api', 'account')
        except RemoteError as e:
            error = str(e)
            if 'API-key format invalid' in error:
                return False, 'Provided API Key is in invalid Format'
            if 'Signature for this request is not valid' in error:
                return False, 'Provided API Secret is malformed'
            if 'Invalid API-key, IP, or permissions for action' in error:
                return False, 'API Key does not match the given secret'
            if 'Timestamp for this request was' in error:
                return False, (
                    f"Local system clock is not in sync with {self.name} server. "
                    f"Try syncing your system's clock"
                )
            # else reraise
            raise

        return True, ''

    def api_query(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: Optional[Dict] = None,
    ) -> Union[List, Dict]:
        """Performs a binance api query

        May raise:
         - RemoteError
         - BinancePermissionError
        """
        call_options = options.copy() if options else {}

        while True:
            if 'signature' in call_options:
                del call_options['signature']

            is_v3_api_method = api_type == 'api' and method in V3_METHODS
            is_new_futures_api = api_type in ('fapi', 'dapi')
            api_version = 3  # public methos are v3
            if method not in PUBLIC_METHODS:  # api call needs signature
                if api_type in ('sapi', 'dapi'):
                    api_version = 1
                elif api_type == 'fapi':
                    api_version = 2
                elif is_v3_api_method:
                    api_version = 3
                else:
                    raise AssertionError(
                        f'Should never get to signed binance api call for '
                        f'api_type: {api_type} and method {method}',
                    )

                # Recommended recvWindows is 5000 but we get timeouts with it
                call_options['recvWindow'] = 10000
                call_options['timestamp'] = str(ts_now_in_ms() + self.offset_ms)
                signature = hmac.new(
                    self.secret,
                    urlencode(call_options).encode('utf-8'),
                    hashlib.sha256,
                ).hexdigest()
                call_options['signature'] = signature

            api_subdomain = api_type if is_new_futures_api else 'api'
            request_url = (
                f'https://{api_subdomain}.{self.uri}{api_type}/v{str(api_version)}/{method}?'
            )
            request_url += urlencode(call_options)
            log.debug(f'{self.name} API request', request_url=request_url)
            try:
                response = self.session.get(request_url, timeout=DEFAULT_TIMEOUT_TUPLE)
            except requests.exceptions.RequestException as e:
                raise RemoteError(
                    f'{self.name} API request failed due to {str(e)}',
                ) from e

            if response.status_code not in (200, 418, 429):
                code = 'no code found'
                msg = 'no message found'
                try:
                    result = json.loads(response.text)
                    if isinstance(result, dict):
                        code = result.get('code', code)
                        msg = result.get('msg', msg)
                except JSONDecodeError:
                    pass

                if 'Invalid symbol' in msg and method == 'myTrades':
                    assert options, 'We always provide options for myTrades call'
                    symbol = options.get('symbol', 'no symbol given')
                    # Binance does not return trades for delisted markets. It also may
                    # return a delisted market in the active market endpoints, so we
                    # need to handle it here.
                    log.debug(f'Couldnt query {self.name} trades for {symbol} since its delisted')
                    return []

                exception_class: Union[Type[RemoteError], Type[BinancePermissionError]]
                if response.status_code == 401 and code == REJECTED_MBX_KEY:
                    # Either API key permission error or if futures/dapi then not enabled yet
                    exception_class = BinancePermissionError
                else:
                    exception_class = RemoteError

                raise exception_class(
                    '{} API request {} for {} failed with HTTP status '
                    'code: {}, error code: {} and error message: {}'.format(
                        self.name,
                        response.url,
                        method,
                        response.status_code,
                        code,
                        msg,
                    ))

            if response.status_code in (418, 429):
                # Binance has limits and if we hit them we should backoff.
                # A Retry-After header is sent with a 418 or 429 responses and
                # will give the number of seconds required to wait, in the case
                # of a 429, to prevent a ban, or, in the case of a 418, until
                # the ban is over.
                # https://binance-docs.github.io/apidocs/spot/en/#limits
                retry_after = int(response.headers.get('retry-after', '0'))
                # Spoiler. They actually seem to always return 0 here. So we don't
                # wait at all. Won't be much of an improvement but force 1 sec wait if 0 returns
                retry_after = max(1, retry_after)  # wait at least 1 sec even if api says otherwise
                log.debug(
                    f'Got status code {response.status_code} from {self.name}. Backing off',
                    seconds=retry_after,
                )
                if retry_after > RETRY_AFTER_LIMIT:
                    raise RemoteError(
                        '{} API request {} for {} failed with HTTP status '
                        'code: {} due to a too long retry after value ({} > {})'.format(
                            self.name,
                            response.url,
                            method,
                            response.status_code,
                            retry_after,
                            RETRY_AFTER_LIMIT,
                        ))

                gevent.sleep(retry_after)
                continue

            # else success
            break

        try:
            json_ret = json.loads(response.text)
        except JSONDecodeError as e:
            raise RemoteError(
                f'{self.name} returned invalid JSON response: {response.text}',
            ) from e
        return json_ret

    def api_query_dict(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: Optional[Dict] = None,
    ) -> Dict:
        """May raise RemoteError and BinancePermissionError due to api_query"""
        result = self.api_query(api_type, method, options)
        if not isinstance(result, dict):
            error_msg = f'Expected dict but did not get it in {self.name} api response.'
            log.error(f'{error_msg}. Got: {result}')
            raise RemoteError(error_msg)

        return result

    def api_query_list(
            self,
            api_type: BINANCE_API_TYPE,
            method: str,
            options: Optional[Dict] = None,
    ) -> List:
        """May raise RemoteError and BinancePermissionError due to api_query"""
        result = self.api_query(api_type, method, options)
        if isinstance(result, Dict):
            if 'data' in result:
                result = result['data']
            elif 'total' in result and result['total'] == 0:
                # This is a completely undocumented behavior of their api seen in the wild.
                # At least one endpoint (/sapi/v1/fiat/payments) can omit the data
                # key in the response object instead of returning an empty list like
                # other endpoints.
                # {'code': '000000', 'message': 'success', 'success': True, 'total': 0}
                return []

        if not isinstance(result, list):
            error_msg = f'Expected list but did not get it in {self.name} api response.'
            log.error(f'{error_msg}. Got: {result}')
            raise RemoteError(error_msg)

        return result

    def _query_spot_balances(
            self,
            balances: DefaultDict[AssetWithSymbol, Balance],
    ) -> DefaultDict[AssetWithSymbol, Balance]:
        account_data = self.api_query_dict('api', 'account')
        binance_balances = account_data.get('balances', None)
        if not binance_balances:
            raise RemoteError('Binance spot balances response did not contain the balances key')

        for entry in binance_balances:
            try:
                # force string https://github.com/rotki/rotki/issues/2342
                asset_symbol = str(entry['asset'])
                free = deserialize_asset_amount(entry['free'])
                locked = deserialize_asset_amount(entry['locked'])
            except KeyError as e:
                raise RemoteError(f'Binance spot balance asset entry did not contain key {str(e)}') from e  # noqa: E501
            except DeserializationError as e:
                raise RemoteError('Failed to deserialize an amount from binance spot balance asset entry') from e  # noqa: E501

            if len(asset_symbol) >= 5 and asset_symbol.startswith('LD'):
                # Some lending coins also appear to start with the LD prefix. Ignore them
                continue

            amount = free + locked
            if amount == ZERO:
                continue

            try:
                asset = asset_from_binance(asset_symbol)
            except UnsupportedAsset as e:
                if e.asset_name != 'ETF':
                    self.msg_aggregator.add_warning(
                        f'Found unsupported {self.name} asset {e.asset_name}. '
                        f'Ignoring its balance query.',
                    )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown {self.name} asset {e.asset_name}. '
                    f'Ignoring its balance query.',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Found {self.name} asset with non-string type {type(entry["asset"])}. '
                    f'Ignoring its balance query.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balances[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return balances

    def _query_lending_balances(
            self,
            balances: DefaultDict[AssetWithSymbol, Balance],
    ) -> DefaultDict[AssetWithSymbol, Balance]:
        """Queries binance lending balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        data = self.api_query_dict('sapi', 'lending/union/account')
        positions = data.get('positionAmountVos', None)
        if positions is None:
            raise RemoteError(
                f'Could not find key positionAmountVos in lending account data '
                f'{data} returned by {self.name}.',
            )

        for entry in positions:
            try:
                amount = deserialize_asset_amount(entry['amount'])
                if amount == ZERO:
                    continue

                asset = asset_from_binance(entry['asset'])
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported {self.name} asset {e.asset_name}. '
                    f'Ignoring its lending balance query.',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown {self.name} asset {e.asset_name}. '
                    f'Ignoring its lending balance query.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error at deserializing {self.name} asset. {msg}. '
                    f'Ignoring its lending balance query.',
                )
                continue

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping balance entry',
                )
                continue

            balances[asset] += Balance(
                amount=amount,
                usd_value=amount * usd_price,
            )

        return balances

    def _query_cross_collateral_futures_balances(
            self,
            balances: DefaultDict[AssetWithSymbol, Balance],
    ) -> DefaultDict[AssetWithSymbol, Balance]:
        """Queries binance collateral future balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        futures_response = self.api_query_dict('sapi', 'futures/loan/wallet')
        try:
            cross_collaterals = futures_response['crossCollaterals']
            for entry in cross_collaterals:
                amount = deserialize_asset_amount(entry['locked'])
                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_binance(entry['collateralCoin'])
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported {self.name} asset {e.asset_name}. '
                        f'Ignoring its futures balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown {self.name} asset {e.asset_name}. '
                        f'Ignoring its futures balance query.',
                    )
                    continue
                except DeserializationError:
                    self.msg_aggregator.add_error(
                        f'Found {self.name} asset with non-string type '
                        f'{type(entry["asset"])}. Ignoring its futures balance query.',
                    )
                    continue

                try:
                    usd_price = Inquirer().find_usd_price(asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                balances[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )

        except KeyError as e:
            self.msg_aggregator.add_error(
                f'At {self.name} futures balance query did not find expected key '
                f'{str(e)}. Skipping futures query...',
            )

        return balances

    def _query_margined_fapi(self, balances: DefaultDict[AssetWithSymbol, Balance]) -> DefaultDict[AssetWithSymbol, Balance]:  # noqa: E501
        """Only a convenience function to give same interface as other query methods"""
        return self._query_margined_futures_balances('fapi', balances)

    def _query_margined_dapi(self, balances: DefaultDict[AssetWithSymbol, Balance]) -> DefaultDict[AssetWithSymbol, Balance]:  # noqa: E501
        """Only a convenience function to give same interface as other query methods"""
        return self._query_margined_futures_balances('dapi', balances)

    def _query_margined_futures_balances(
            self,
            api_type: Literal['fapi', 'dapi'],
            balances: DefaultDict[AssetWithSymbol, Balance],
    ) -> DefaultDict[AssetWithSymbol, Balance]:
        """Queries binance margined future balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """
        try:
            response = self.api_query_list(api_type, 'balance')
        except BinancePermissionError as e:
            log.warning(
                f'Insufficient permission to query {self.name} {api_type} balances.'
                f'Skipping query. Response details: {str(e)}',
            )
            return balances

        try:
            for entry in response:
                amount = deserialize_asset_amount(entry['balance'])
                if amount == ZERO:
                    continue

                try:
                    asset = asset_from_binance(entry['asset'])
                except UnsupportedAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unsupported {self.name} asset {e.asset_name}. '
                        f'Ignoring its margined futures balance query.',
                    )
                    continue
                except UnknownAsset as e:
                    self.msg_aggregator.add_warning(
                        f'Found unknown {self.name} asset {e.asset_name}. '
                        f'Ignoring its margined futures balance query.',
                    )
                    continue
                except DeserializationError:
                    self.msg_aggregator.add_error(
                        f'Found {self.name} asset with non-string type '
                        f'{type(entry["asset"])}. Ignoring its margined futures balance query.',
                    )
                    continue

                try:
                    usd_price = Inquirer().find_usd_price(asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing {self.name} balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping margined futures balance entry',
                    )
                    continue

                balances[asset] += Balance(
                    amount=amount,
                    usd_value=amount * usd_price,
                )

        except KeyError as e:
            self.msg_aggregator.add_error(
                f'At {self.name} margined futures balance query did not find '
                f'expected key {str(e)}. Skipping margined futures query...',
            )

        return balances

    def _query_pools_balances(
            self,
            balances: DefaultDict[AssetWithSymbol, Balance],
    ) -> DefaultDict[AssetWithSymbol, Balance]:
        """Queries binance pool balances and if any found adds them to `balances`

        May raise:
        - RemoteError
        """

        def process_pool_asset(asset_name: str, asset_amount: FVal) -> None:
            if asset_amount == ZERO:
                return None

            try:
                asset = asset_from_binance(asset_name)
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported {self.name} asset {asset_name}. '
                    f'Ignoring its {self.name} pool balance query. {str(e)}',
                )
                return None
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown {self.name} asset {asset_name}. '
                    f'Ignoring its {self.name} pool balance query. {str(e)}',
                )
                return None
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'{self.name} balance deserialization error '
                    f'for asset {asset_name}: {str(e)}. Skipping entry.',
                )
                return None

            try:
                usd_price = Inquirer().find_usd_price(asset)
            except RemoteError as e:
                self.msg_aggregator.add_error(
                    f'Error processing {self.name} balance entry due to inability to '
                    f'query USD price: {str(e)}. Skipping {self.name} pool balance entry',
                )
                return None

            balances[asset] += Balance(
                amount=asset_amount,
                usd_value=asset_amount * usd_price,
            )
            return None

        try:
            response = self.api_query('sapi', 'bswap/liquidity')
        except BinancePermissionError as e:
            log.warning(
                f'Insufficient permission to query {self.name} pool balances.'
                f'Skipping query. Response details: {str(e)}',
            )
            return balances

        try:
            for entry in response:
                for asset_name, asset_amount in entry['share']['asset'].items():
                    process_pool_asset(asset_name, FVal(asset_amount))
        except (KeyError, AttributeError) as e:
            self.msg_aggregator.add_error(
                f'At {self.name} pool balances got unexpected data format. '
                f'Skipping them in the balance query. Check logs for details',
            )
            if isinstance(e, KeyError):
                msg = f'Missing key {str(e)}'
            else:
                msg = str(e)
            log.error(
                f'Unexpected data format returned by {self.name} pools. '
                f'Data: {response}. Error: {msg}',
            )

        return balances

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            self.first_connection()
            returned_balances: DefaultDict[AssetWithSymbol, Balance] = defaultdict(Balance)
            returned_balances = self._query_spot_balances(returned_balances)
            if self.location != Location.BINANCEUS:
                for method in (
                        self._query_lending_balances,
                        self._query_cross_collateral_futures_balances,
                        self._query_margined_fapi,
                        self._query_margined_dapi,
                        self._query_pools_balances,
                ):
                    try:
                        returned_balances = method(returned_balances)
                    except RemoteError as e:  # errors in any of these methods should not be fatal
                        log.warning(f'Failed to query binance method {method.__name__} due to {str(e)}')  # noqa: E501

        except RemoteError as e:
            msg = (
                f'{self.name} account API request failed. '
                f'Could not reach binance due to {str(e)}'
            )
            self.msg_aggregator.add_error(msg)
            return None, msg

        log.debug(
            f'{self.name} balance query result',
            balances=returned_balances,
        )
        return dict(returned_balances), ''

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        """

        May raise due to api query and unexpected id:
        - RemoteError
        - BinancePermissionError
        """
        self.first_connection()
        if self.selected_pairs is not None:
            iter_markets = list(set(self.selected_pairs).intersection(set(self._symbols_to_pair.keys())))  # noqa: E501
        else:
            iter_markets = list(self._symbols_to_pair.keys())

        raw_data = []
        # Limit of results to return. 1000 is max limit according to docs
        limit = 1000
        for symbol in iter_markets:
            last_trade_id = 0
            len_result = limit
            while len_result == limit:
                # We know that myTrades returns a list from the api docs
                result = self.api_query_list(
                    'api',
                    'myTrades',
                    options={
                        'symbol': symbol,
                        'fromId': last_trade_id,
                        'limit': limit,
                        # Not specifying them since binance does not seem to
                        # respect them and always return all trades
                        # 'startTime': start_ts * 1000,
                        # 'endTime': end_ts * 1000,
                    })
                if result:
                    try:
                        last_trade_id = int(result[-1]['id']) + 1
                    except (ValueError, KeyError, IndexError) as e:
                        raise RemoteError(
                            f'Could not parse id from Binance myTrades api query result: {result}',
                        ) from e

                len_result = len(result)
                log.debug(f'{self.name} myTrades query result', results_num=len_result)
                for r in result:
                    r['symbol'] = symbol
                raw_data.extend(result)

            raw_data.sort(key=lambda x: x['time'])

        trades = []
        for raw_trade in raw_data:
            try:
                trade = trade_from_binance(
                    binance_trade=raw_trade,
                    binance_symbols_to_pair=self.symbols_to_pair,
                    location=self.location,
                )
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} trade with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnsupportedAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found {self.name} trade with unsupported asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    f'Error processing a {self.name} trade. Check logs '
                    f'for details. Ignoring it.',
                )
                log.error(
                    f'Error processing a {self.name} trade',
                    trade=raw_trade,
                    error=msg,
                )
                continue

            # Since binance does not respect the given timestamp range, limit the range here
            if trade.timestamp < start_ts:
                continue

            if trade.timestamp > end_ts:
                break

            trades.append(trade)

        fiat_payments = self._query_online_fiat_payments(start_ts=start_ts, end_ts=end_ts)
        if fiat_payments:
            trades += fiat_payments
            trades.sort(key=lambda x: x.timestamp)

        return trades, (start_ts, end_ts)

    def _query_online_fiat_payments(self, start_ts: Timestamp, end_ts: Timestamp) -> List[Trade]:
        if self.location == Location.BINANCEUS:
            return []  # dont exist for Binance US: https://github.com/rotki/rotki/issues/3664

        fiat_buys = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='fiat/payments',
            additional_options={'transactionType': 0},
        )
        log.debug(f'{self.name} fiat buys history result', results_num=len(fiat_buys))
        fiat_sells = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='fiat/payments',
            additional_options={'transactionType': 1},
        )
        log.debug(f'{self.name} fiat sells history result', results_num=len(fiat_sells))

        trades = []
        for idx, raw_fiat in enumerate(fiat_buys + fiat_sells):
            trade_type = TradeType.BUY if idx < len(fiat_buys) else TradeType.SELL
            trade = self._deserialize_fiat_payment(raw_fiat, trade_type=trade_type)
            if trade:
                trades.append(trade)

        return trades

    def _deserialize_fiat_payment(
            self,
            raw_data: Dict[str, Any],
            trade_type: TradeType,
    ) -> Optional[Trade]:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if 'status' not in raw_data or raw_data['status'] != 'Completed':
                log.error(
                    f'Found {str(self.location)} fiat payment with failed status. Ignoring it.',
                )
                return None

            fiat_asset = asset_from_binance(raw_data['fiatCurrency'])
            tx_id = get_key_if_has_val(raw_data, 'orderNo')
            timestamp = deserialize_timestamp_from_intms(raw_data['createTime'])
            fee = Fee(deserialize_asset_amount(raw_data['totalFee']))
            link_str = str(tx_id) if tx_id else ''
            crypto_asset = asset_from_binance(raw_data['cryptoCurrency'])
            obtain_amount = deserialize_asset_amount_force_positive(
                raw_data['obtainAmount'],
            )
            rate = deserialize_price(raw_data['price'])
            base_asset = crypto_asset
            quote_asset = fiat_asset
            return Trade(
                timestamp=timestamp,
                location=self.location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=trade_type,
                amount=obtain_amount,
                rate=rate,
                fee=fee,
                fee_currency=quote_asset,
                link=link_str,
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} fiat payment with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} fiat payment with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {str(self.location)} fiat payment. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {str(self.location)} fiat payment',
                asset_movement=raw_data,
                error=msg,
            )

        return None

    def _deserialize_fiat_movement(
            self,
            raw_data: Dict[str, Any],
            category: AssetMovementCategory,
    ) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if 'status' not in raw_data or raw_data['status'] not in ('Successful', 'Finished'):
                log.error(
                    f'Found {str(self.location)} fiat deposit/withdrawal with failed status. Ignoring it.',  # noqa: E501
                )
                return None

            asset = asset_from_binance(raw_data['fiatCurrency'])
            tx_id = get_key_if_has_val(raw_data, 'orderNo')
            timestamp = deserialize_timestamp_from_intms(raw_data['createTime'])
            fee = Fee(deserialize_asset_amount(raw_data['totalFee']))
            link_str = str(tx_id) if tx_id else ''
            amount = deserialize_asset_amount_force_positive(raw_data['amount'])
            return AssetMovement(
                location=self.location,
                category=category,
                address=deserialize_asset_movement_address(raw_data, 'address', asset),
                transaction_id=tx_id,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee_asset=asset,
                fee=fee,
                link=link_str,
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} fiat deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} fiat deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {str(self.location)} fiat deposit/withdrawal. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {str(self.location)} fiat deposit/withdrawal',
                asset_movement=raw_data,
                error=msg,
            )

        return None

    def _deserialize_asset_movement(self, raw_data: Dict[str, Any]) -> Optional[AssetMovement]:
        """Processes a single deposit/withdrawal from binance and deserializes it

        Can log error/warning and return None if something went wrong at deserialization
        """
        try:
            if 'insertTime' in raw_data:
                category = AssetMovementCategory.DEPOSIT
                timestamp = deserialize_timestamp_from_intms(raw_data['insertTime'])
                fee = Fee(ZERO)
            else:
                category = AssetMovementCategory.WITHDRAWAL
                timestamp = deserialize_timestamp_from_date(
                    date=raw_data['applyTime'],
                    formatstr='%Y-%m-%d %H:%M:%S',
                    location='binance withdrawal',
                    skip_milliseconds=True,
                )
                fee = Fee(deserialize_asset_amount(raw_data['transactionFee']))

            asset = asset_from_binance(raw_data['coin'])
            tx_id = get_key_if_has_val(raw_data, 'txId')
            internal_id = get_key_if_has_val(raw_data, 'id')
            link_str = str(internal_id) if internal_id else str(tx_id) if tx_id else ''
            return AssetMovement(
                location=self.location,
                category=category,
                address=deserialize_asset_movement_address(raw_data, 'address', asset),
                transaction_id=tx_id,
                timestamp=timestamp,
                asset=asset,
                amount=deserialize_asset_amount_force_positive(raw_data['amount']),
                fee_asset=asset,
                fee=fee,
                link=link_str,
            )

        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} deposit/withdrawal with unknown asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'Found {str(self.location)} deposit/withdrawal with unsupported asset '
                f'{e.asset_name}. Ignoring it.',
            )
        except (DeserializationError, KeyError) as e:
            msg = str(e)
            if isinstance(e, KeyError):
                msg = f'Missing key entry for {msg}.'
            self.msg_aggregator.add_error(
                f'Error processing a {str(self.location)} deposit/withdrawal. Check logs '
                f'for details. Ignoring it.',
            )
            log.error(
                f'Error processing a {str(self.location)} deposit/withdrawal',
                asset_movement=raw_data,
                error=msg,
            )

        return None

    def _api_query_list_within_time_delta(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            time_delta: Timestamp,
            api_type: BINANCE_API_TYPE,
            method: Literal[
                'capital/deposit/hisrec',
                'capital/withdraw/history',
                'fiat/orders',
                'fiat/payments',
            ],
            additional_options: Dict = None,
    ) -> List[Dict[str, Any]]:
        """Request via `api_query_dict()` from `start_ts` `end_ts` using a time
        delta (offset) less than `time_delta`.

        Be aware of:
          - If `start_ts` equals zero, the Binance launch timestamp is used
          (from BINANCE_LAUNCH_TS). This value is not stored in the
          `used_query_ranges` table, but 0.
          - Timestamps are converted to milliseconds.
        """
        results: List[Dict[str, Any]] = []
        # Create required time references in milliseconds
        start_ts = Timestamp(start_ts * 1000)
        end_ts = Timestamp(end_ts * 1000)
        offset = time_delta * 1000 - 1  # less than time_delta
        if start_ts == Timestamp(0):
            from_ts = BINANCE_LAUNCH_TS * 1000
        else:
            from_ts = start_ts

        to_ts = (
            from_ts + offset  # Case request with offset
            if end_ts - from_ts > offset
            else end_ts  # Case request without offset (1 request)
        )
        while True:
            options = {
                'timestamp': ts_now_in_ms(),
                'startTime': from_ts,
                'endTime': to_ts,
            }
            if additional_options:
                options.update(additional_options)
            result = self.api_query_list(api_type, method, options=options)
            results.extend(result)
            # Case stop requesting
            if to_ts >= end_ts:
                break

            from_ts = to_ts + 1
            to_ts = min(to_ts + offset, end_ts)

        return results

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """
        Be aware of:
          - Timestamps must be in milliseconds.
          - There must be less than 90 days between start and end timestamps.

        Deposit & Withdraw history documentation:
        https://binance-docs.github.io/apidocs/spot/en/#deposit-history-user_data
        https://binance-docs.github.io/apidocs/spot/en/#withdraw-history-user_data
        """
        deposits = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='capital/deposit/hisrec',
        )
        log.debug(f'{self.name} deposit history result', results_num=len(deposits))

        withdraws = self._api_query_list_within_time_delta(
            start_ts=start_ts,
            end_ts=end_ts,
            time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
            api_type='sapi',
            method='capital/withdraw/history',
        )
        log.debug(f'{self.name} withdraw history result', results_num=len(withdraws))

        if self.location != Location.BINANCEUS:
            # dont exist for Binance US: https://github.com/rotki/rotki/issues/3664
            fiat_deposits = self._api_query_list_within_time_delta(
                start_ts=Timestamp(0),
                end_ts=end_ts,
                time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                api_type='sapi',
                method='fiat/orders',
                additional_options={'transactionType': 0},
            )
            log.debug(f'{self.name} fiat deposit history result', results_num=len(fiat_deposits))
            fiat_withdraws = self._api_query_list_within_time_delta(
                start_ts=Timestamp(0),
                end_ts=end_ts,
                time_delta=API_TIME_INTERVAL_CONSTRAINT_TS,
                api_type='sapi',
                method='fiat/orders',
                additional_options={'transactionType': 1},
            )
            log.debug(f'{self.name} fiat withdraw history result', results_num=len(fiat_withdraws))
        else:
            fiat_deposits, fiat_withdraws = [], []

        movements = []
        for raw_movement in deposits + withdraws:
            movement = self._deserialize_asset_movement(raw_movement)
            if movement:
                movements.append(movement)

        for idx, fiat_movement in enumerate(fiat_deposits + fiat_withdraws):
            category = AssetMovementCategory.DEPOSIT if idx < len(fiat_deposits) else AssetMovementCategory.WITHDRAWAL  # noqa: E501
            movement = self._deserialize_fiat_movement(fiat_movement, category=category)
            if movement:
                movements.append(movement)

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for binance

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for binance
