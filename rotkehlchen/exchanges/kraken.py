# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/clikraken
import base64
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import gevent
import requests
from requests import Response

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import KRAKEN_TO_WORLD, asset_from_kraken
from rotkehlchen.constants import KRAKEN_API_VERSION, KRAKEN_BASE_URL
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH2
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.constants.timing import DEFAULT_TIMEOUT_TUPLE
from rotkehlchen.errors import (
    DeserializationError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
)
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_kraken,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KRAKEN_DELISTED = ('XDAO', 'XXVN', 'ZKRW', 'XNMC', 'BSV', 'XICN')
KRAKEN_PUBLIC_METHODS = ('AssetPairs', 'Assets')
KRAKEN_QUERY_TRIES = 8
KRAKEN_BACKOFF_DIVIDEND = 15
MAX_CALL_COUNTER_INCREASE = 2  # Trades and Ledger produce the max increase


def kraken_to_world_pair(pair: str) -> Tuple[Asset, Asset]:
    """Turns a pair from kraken to our base/quote asset tuple

    Can throw:
        - UknownAsset if one of the assets of the pair are not known
        - DeserializationError if one of the assets is not a sting
        - UnprocessableTradePair if the pair can't be processed and
          split into its base/quote assets
"""
    # handle dark pool pairs
    if pair[-2:] == '.d':
        pair = pair[:-2]

    if len(pair) == 6 and pair[0:3] in ('EUR', 'USD', 'AUD'):
        # This is for the FIAT to FIAT pairs that kraken introduced
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair == 'ETHDAI':
        return A_ETH, A_DAI
    elif pair == 'ETH2.SETH':
        return A_ETH2, A_ETH
    elif pair[0:2] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:2]
        quote_asset_str = pair[2:]
    elif pair[0:3] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair[0:3] in ('XBT', 'ETH', 'XDG', 'LTC', 'XRP'):
        # Some assets can have the 'X' prefix omitted for some pairs
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair[0:4] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:4]
        quote_asset_str = pair[4:]
    elif pair[0:5] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:5]
        quote_asset_str = pair[5:]
    elif pair[0:6] in KRAKEN_TO_WORLD:
        base_asset_str = pair[0:6]
        quote_asset_str = pair[6:]
    else:
        raise UnprocessableTradePair(pair)

    base_asset = asset_from_kraken(base_asset_str)
    quote_asset = asset_from_kraken(quote_asset_str)
    return base_asset, quote_asset


def trade_from_kraken(kraken_trade: Dict[str, Any]) -> Trade:
    """Turn a kraken trade returned from kraken trade history to our common trade
    history format

    - Can raise UnknownAsset due to kraken_to_world_pair
    - Can raise UnprocessableTradePair due to kraken_to_world_pair
    - Can raise DeserializationError due to dict entries not being as expected
    - Can raise KeyError due to dict entries missing an expected entry
    """
    base_asset, quote_asset = kraken_to_world_pair(kraken_trade['pair'])

    timestamp = deserialize_timestamp_from_kraken(kraken_trade['time'])
    amount = deserialize_asset_amount(kraken_trade['vol'])
    cost = deserialize_price(kraken_trade['cost'])
    fee = deserialize_fee(kraken_trade['fee'])
    order_type = deserialize_trade_type(kraken_trade['type'])
    rate = deserialize_price(kraken_trade['price'])

    # pylint does not seem to see that Price is essentially FVal
    if not cost.is_close(amount * rate):  # pylint: disable=no-member
        log.warning(f'cost ({cost}) != amount ({amount}) * rate ({rate}) for kraken trade')

    log.debug(
        'Processing kraken Trade',
        timestamp=timestamp,
        order_type=order_type,
        kraken_pair=kraken_trade['pair'],
        base_asset=base_asset,
        quote_asset=quote_asset,
        amount=amount,
        cost=cost,
        fee=fee,
        rate=rate,
    )

    # Kraken trades can have the same ordertxid and postxid for different trades ..
    # Also note postxid is optional and can be missing
    # The only thing that could differentiate them is timestamps in the milliseconds range
    # For example here are parts of two different kraken_trade:
    # {'ordertxid': 'AM4ZOZ-GLEMD-ZICOGR', 'postxid': 'AKH2SE-M7IF5-CFI7AT',
    # 'pair': 'XXBTZEUR', 'time': FVal(1561161486.2955)
    # {'ordertxid': 'AM4ZOZ-GLEMD-ZICOGR', 'postxid': 'AKH2SE-M7IF5-CFI7AT',
    # 'pair': 'XXBTZEUR', 'time': FVal(1561161486.3005)
    #
    # In order to counter this for the unique exchange trade link we are going
    # to use a concatenation of the above
    exchange_uuid = (
        str(kraken_trade['ordertxid']) +
        str(kraken_trade.get('postxid', '')) +  # postxid is optional
        str(kraken_trade['time'])
    )

    return Trade(
        timestamp=timestamp,
        location=Location.KRAKEN,
        base_asset=base_asset,
        quote_asset=quote_asset,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=quote_asset,
        link=exchange_uuid,
    )


def _check_and_get_response(response: Response, method: str) -> Union[str, Dict]:
    """Checks the kraken response and if it's succesfull returns the result.

    If there is recoverable error a string is returned explaining the error
    May raise:
    - RemoteError if there is an unrecoverable/unexpected remote error
    """
    if response.status_code in (520, 525, 504):
        log.debug(f'Kraken returned status code {response.status_code}')
        return 'Usual kraken 5xx shenanigans'
    if response.status_code != 200:
        raise RemoteError(
            'Kraken API request {} for {} failed with HTTP status '
            'code: {}'.format(
                response.url,
                method,
                response.status_code,
            ))

    try:
        decoded_json = jsonloads_dict(response.text)
    except json.decoder.JSONDecodeError as e:
        raise RemoteError(f'Invalid JSON in Kraken response. {e}') from e

    error = decoded_json.get('error', None)
    if error:
        if isinstance(error, list) and len(error) != 0:
            error = error[0]

        if 'Rate limit exceeded' in error:
            log.debug(f'Kraken: Got rate limit exceeded error: {error}')
            return 'Rate limited exceeded'

        # else
        raise RemoteError(error)

    result = decoded_json.get('result', None)
    if result is None:
        if method == 'Balance':
            return {}

        raise RemoteError(f'Missing result in kraken response for {method}')

    return result


class KrakenAccountType(SerializableEnumMixin):
    STARTER = 0
    INTERMEDIATE = 1
    PRO = 2


DEFAULT_KRAKEN_ACCOUNT_TYPE = KrakenAccountType.STARTER


class Kraken(ExchangeInterface):  # lgtm[py/missing-call-to-init]
    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            kraken_account_type: Optional[KrakenAccountType] = None,
    ):
        super().__init__(
            name=name,
            location=Location.KRAKEN,
            api_key=api_key,
            secret=secret,
            database=database,
        )
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({'API-Key': self.api_key})
        self.set_account_type(kraken_account_type)
        self.call_counter = 0
        self.last_query_ts = 0

    def set_account_type(self, account_type: Optional[KrakenAccountType]) -> None:
        if account_type is None:
            account_type = DEFAULT_KRAKEN_ACCOUNT_TYPE

        self.account_type = account_type
        if self.account_type == KrakenAccountType.STARTER:
            self.call_limit = 15
            self.reduction_every_secs = 3
        elif self.account_type == KrakenAccountType.INTERMEDIATE:
            self.call_limit = 20
            self.reduction_every_secs = 2
        else:  # Pro
            self.call_limit = 20
            self.reduction_every_secs = 1

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        changed = super().edit_exchange_credentials(api_key, api_secret, passphrase)
        if api_key is not None:
            self.session.headers.update({'API-Key': self.api_key})

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

        account_type = kwargs.get('kraken_account_type')
        if account_type is None:
            return success, msg

        # here we can finally update the account type
        self.set_account_type(account_type)
        return True, ''

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validates that the Kraken API Key is good for usage in Rotkehlchen

        Makes sure that the following permission are given to the key:
        - Ability to query funds
        - Ability to query open/closed trades
        - Ability to query ledgers
        """
        valid, msg = self._validate_single_api_key_action('Balance')
        if not valid:
            return False, msg
        valid, msg = self._validate_single_api_key_action(
            method_str='TradesHistory',
            req={'start': 0, 'end': 0},
        )
        if not valid:
            return False, msg
        valid, msg = self._validate_single_api_key_action(
            method_str='Ledgers',
            req={'start': 0, 'end': 0, 'type': 'deposit'},
        )
        if not valid:
            return False, msg
        return True, ''

    def _validate_single_api_key_action(
            self,
            method_str: str,
            req: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        try:
            self.api_query(method_str, req)
        except (RemoteError, ValueError) as e:
            error = str(e)
            if 'Incorrect padding' in error:
                return False, 'Provided API Key or secret is invalid'
            if 'EAPI:Invalid key' in error:
                return False, 'Provided API Key is invalid'
            if 'EGeneral:Permission denied' in error:
                msg = (
                    'Provided API Key does not have appropriate permissions. Make '
                    'sure that the "Query Funds", "Query Open/Closed Order and Trades"'
                    'and "Query Ledger Entries" actions are allowed for your Kraken API Key.'
                )
                return False, msg

            # else
            log.error(f'Kraken API key validation error: {str(e)}')
            msg = (
                'Unknown error at Kraken API key validation. Perhaps API '
                'Key/Secret combination invalid?'
            )
            return False, msg
        return True, ''

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _manage_call_counter(self, method: str) -> None:
        self.last_query_ts = ts_now()
        if method in ('Ledgers', 'TradesHistory'):
            self.call_counter += 2
        else:
            self.call_counter += 1

    def _query_public(self, method: str, req: Optional[dict] = None) -> Union[Dict, str]:
        """API queries that do not require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})
        """
        if req is None:
            req = {}
        urlpath = f'{KRAKEN_BASE_URL}/{KRAKEN_API_VERSION}/public/{method}'
        try:
            response = self.session.post(urlpath, data=req, timeout=DEFAULT_TIMEOUT_TUPLE)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {str(e)}') from e

        self._manage_call_counter(method)
        return _check_and_get_response(response, method)

    def api_query(self, method: str, req: Optional[dict] = None) -> dict:
        tries = KRAKEN_QUERY_TRIES
        query_method = (
            self._query_public if method in KRAKEN_PUBLIC_METHODS else self._query_private
        )
        while tries > 0:
            if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                # If we are close to the limit, check how much our call counter reduced
                # https://www.kraken.com/features/api#api-call-rate-limit
                secs_since_last_call = ts_now() - self.last_query_ts
                self.call_counter = max(
                    0,
                    self.call_counter - int(secs_since_last_call / self.reduction_every_secs),
                )
                # If still at limit, sleep for an amount big enough for smallest tier reduction
                if self.call_counter + MAX_CALL_COUNTER_INCREASE > self.call_limit:
                    backoff_in_seconds = self.reduction_every_secs * 2
                    log.debug(
                        f'Doing a Kraken API call would now exceed our call counter limit. '
                        f'Backing off for {backoff_in_seconds} seconds',
                        call_counter=self.call_counter,
                    )
                    tries -= 1
                    gevent.sleep(backoff_in_seconds)
                    continue

            log.debug(
                'Kraken API query',
                method=method,
                data=req,
                call_counter=self.call_counter,
            )
            result = query_method(method, req)
            if isinstance(result, str):
                # Got a recoverable error
                backoff_in_seconds = int(KRAKEN_BACKOFF_DIVIDEND / tries)
                log.debug(
                    f'Got recoverable error {result} in a Kraken query of {method}. Will backoff '
                    f'for {backoff_in_seconds} seconds',
                )
                tries -= 1
                gevent.sleep(backoff_in_seconds)
                continue

            # else success
            return result

        raise RemoteError(
            f'After {KRAKEN_QUERY_TRIES} kraken queries for {method} could still not be completed',
        )

    def _query_private(self, method: str, req: Optional[dict] = None) -> Union[Dict, str]:
        """API queries that require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})

        """
        if req is None:
            req = {}

        urlpath = '/' + KRAKEN_API_VERSION + '/private/' + method
        req['nonce'] = int(1000 * time.time())
        post_data = urlencode(req)
        # any unicode strings must be turned to bytes
        hashable = (str(req['nonce']) + post_data).encode()
        message = urlpath.encode() + hashlib.sha256(hashable).digest()
        signature = hmac.new(
            base64.b64decode(self.secret),
            message,
            hashlib.sha512,
        )
        self.session.headers.update({
            'API-Sign': base64.b64encode(signature.digest()),  # type: ignore
        })
        try:
            response = self.session.post(
                KRAKEN_BASE_URL + urlpath,
                data=post_data.encode(),
                timeout=DEFAULT_TIMEOUT_TUPLE,
            )
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Kraken API request failed due to {str(e)}') from e
        self._manage_call_counter(method)

        return _check_and_get_response(response, method)

    # ---- General exchanges interface ----
    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> ExchangeQueryBalances:
        try:
            kraken_balances = self.api_query('Balance', req={})
        except RemoteError as e:
            if "Missing key: 'result'" in str(e):
                # handle https://github.com/rotki/rotki/issues/946
                kraken_balances = {}
            else:
                msg = (
                    'Kraken API request failed. Could not reach kraken due '
                    'to {}'.format(e)
                )
                log.error(msg)
                return None, msg

        assets_balance: DefaultDict[Asset, Balance] = defaultdict(Balance)
        for kraken_name, amount_ in kraken_balances.items():
            try:
                amount = deserialize_asset_amount(amount_)
                if amount == ZERO:
                    continue

                our_asset = asset_from_kraken(kraken_name)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown kraken asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except DeserializationError as e:
                msg = str(e)
                self.msg_aggregator.add_error(
                    'Error processing kraken balance for {kraken_name}. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing kraken balance',
                    kraken_name=kraken_name,
                    amount=amount_,
                    error=msg,
                )
                continue

            balance = Balance(amount=amount)
            if our_asset.identifier != 'KFEE':
                # There is no price value for KFEE. TODO: Shouldn't we then just skip the balance?
                try:
                    usd_price = Inquirer().find_usd_price(our_asset)
                except RemoteError as e:
                    self.msg_aggregator.add_error(
                        f'Error processing kraken balance entry due to inability to '
                        f'query USD price: {str(e)}. Skipping balance entry',
                    )
                    continue

                balance.usd_value = balance.amount * usd_price

            assets_balance[our_asset] += balance
            log.debug(
                'kraken balance query result',
                currency=our_asset,
                amount=balance.amount,
                usd_value=balance.usd_value,
            )

        return dict(assets_balance), ''

    def query_until_finished(
            self,
            endpoint: str,
            keyname: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            extra_dict: Optional[dict] = None,
    ) -> Tuple[List, bool]:
        """ Abstracting away the functionality of querying a kraken endpoint where
        you need to check the 'count' of the returned results and provide sufficient
        calls with enough offset to gather all the data of your query.
        """
        result: List = []

        with_errors = False
        log.debug(
            f'Querying Kraken {endpoint} from {start_ts} to '
            f'{end_ts} with extra_dict {extra_dict}',
        )
        response = self._query_endpoint_for_period(
            endpoint=endpoint,
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict=extra_dict,
        )
        count = response['count']
        offset = len(response[keyname])
        result.extend(response[keyname].values())

        log.debug(f'Kraken {endpoint} Query Response with count:{count}')

        while offset < count:
            log.debug(
                f'Querying Kraken {endpoint} from {start_ts} to {end_ts} '
                f'with offset {offset} and extra_dict {extra_dict}',
            )
            try:
                response = self._query_endpoint_for_period(
                    endpoint=endpoint,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    offset=offset,
                    extra_dict=extra_dict,
                )
            except RemoteError as e:
                with_errors = True
                log.error(
                    f'One of krakens queries when querying endpoint for period failed '
                    f'with {str(e)}. Returning only results we have.',
                )
                break

            if count != response['count']:
                log.error(
                    f'Kraken unexpected response while querying endpoint for period. '
                    f'Original count was {count} and response returned {response["count"]}',
                )
                with_errors = True
                break

            response_length = len(response[keyname])
            offset += response_length
            if response_length == 0 and offset != count:
                # If we have provided specific filtering then this is a known
                # issue documented below, so skip the warning logging
                # https://github.com/rotki/rotki/issues/116
                if extra_dict:
                    break
                # it is possible that kraken misbehaves and either does not
                # send us enough results or thinks it has more than it really does
                log.warning(
                    'Missing {} results when querying kraken endpoint {}'.format(
                        count - offset, endpoint),
                )
                with_errors = True
                break

            result.extend(response[keyname].values())

        return result, with_errors

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        result, with_errors = self.query_until_finished(
            endpoint='TradesHistory',
            keyname='trades',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        # And now turn it from kraken trade to our own trade format
        trades = []
        max_ts = 0
        for raw_data in result:
            try:
                new_trade = trade_from_kraken(raw_data)
                trades.append(new_trade)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found kraken trade with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except UnprocessableTradePair as e:
                self.msg_aggregator.add_error(
                    f'Found kraken trade with unprocessable pair '
                    f'{e.pair}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Error processing a kraken trade. Check logs '
                    'for details. Ignoring it.',
                )
                log.error(
                    'Error processing a kraken trade',
                    trade=raw_data,
                    error=msg,
                )
                continue

            max_ts = max(new_trade.timestamp, max_ts)

        queried_range = (start_ts, Timestamp(max_ts)) if with_errors else (start_ts, end_ts)
        return trades, queried_range

    def _query_endpoint_for_period(
            self,
            endpoint: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            offset: Optional[int] = None,
            extra_dict: Optional[dict] = None,
    ) -> dict:
        request: Dict[str, Union[Timestamp, int]] = {}
        request['start'] = start_ts
        request['end'] = end_ts
        if offset is not None:
            request['ofs'] = offset
        if extra_dict is not None:
            request.update(extra_dict)
        result = self.api_query(endpoint, request)
        return result

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        result, _ = self.query_until_finished(
            endpoint='Ledgers',
            keyname='ledger',
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict={'type': 'deposit'},
        )
        result2, _ = self.query_until_finished(
            endpoint='Ledgers',
            keyname='ledger',
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict={'type': 'withdrawal'},
        )
        result.extend(result2)

        log.debug('Kraken deposit/withdrawals query result', num_results=len(result))

        movements = []
        for movement in result:
            try:
                asset = asset_from_kraken(movement['asset'])
                movement_type = movement['type']
                if movement_type not in ('deposit', 'withdrawal'):
                    # Other known types: 'transfer'
                    continue  # Can be for moving funds from spot to stake etc.
                movements.append(AssetMovement(
                    location=Location.KRAKEN,
                    category=deserialize_asset_movement_category(movement_type),
                    timestamp=deserialize_timestamp_from_kraken(movement['time']),
                    address=None,  # no data from kraken ledger endpoint
                    transaction_id=None,  # no data from kraken ledger endpoint
                    asset=asset,
                    amount=deserialize_asset_amount_force_positive(movement['amount']),
                    fee_asset=asset,
                    fee=deserialize_fee(movement['fee']),
                    link=str(movement['refid']),
                ))
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unknown kraken asset {e.asset_name}. '
                    f'Ignoring its deposit/withdrawals query.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Failed to deserialize a kraken deposit/withdrawals. '
                    'Check logs for details. Ignoring it.',
                )
                log.error(
                    'Error processing a kraken deposit/withdrawal.',
                    raw_asset_movement=movement,
                    error=msg,
                )
                continue

        return movements

    def query_online_margin_history(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[MarginPosition]:
        return []  # noop for kraken

    def query_online_income_loss_expense(
            self,  # pylint: disable=no-self-use
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> List[LedgerAction]:
        return []  # noop for kraken
