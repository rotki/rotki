#!/usr/bin/env python
#
# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/clikraken
import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

from requests import Response

from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import KRAKEN_API_VERSION, KRAKEN_BASE_URL
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import (
    DeserializationError,
    RecoverableRequestError,
    RemoteError,
    UnknownAsset,
    UnprocessableTradePair,
)
from rotkehlchen.exchanges.data_structures import (
    AssetMovement,
    Trade,
    get_pair_position_asset,
    pair_get_assets,
    trade_pair_from_assets,
)
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_price,
    deserialize_timestamp_from_kraken,
    deserialize_trade_type,
)
from rotkehlchen.typing import ApiKey, ApiSecret, Location, Timestamp, TradePair
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import cache_response_timewise, retry_calls
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


KRAKEN_ASSETS = (
    'ATOM',
    'BAT',
    'XDAO',
    'XETC',
    'XETH',
    'XLTC',
    'XREP',
    'XXBT',
    'XXMR',
    'XXRP',
    'XZEC',
    'ZEUR',
    'ZUSD',
    'ZGBP',
    'ZCAD',
    'ZJPY',
    'ZKRW',
    'XMLN',
    'XICN',
    'GNO',
    'BCH',
    'BSV',
    'XXLM',
    'LINK',
    'DASH',
    'DAI',
    'EOS',
    'USDT',
    'KFEE',
    'ADA',
    'QTUM',
    'XNMC',
    'XXVN',
    'XXDG',
    'XTZ',
    'ICX',
    'WAVES',
)

KRAKEN_DELISTED = ('XDAO', 'XXVN', 'ZKRW', 'XNMC', 'BSV', 'XICN')


def kraken_to_world_pair(pair: str) -> TradePair:
    """Turns a pair from kraken to our pair type

    Can throw:
        - UknownAsset if one of the assets of the pair are not known
        - UnprocessableKrakenPair if the pair can't be processed and
          split into its base/quote assets
"""
    # handle dark pool pairs
    if pair[-2:] == '.d':
        pair = pair[:-2]

    if pair[0:3] in KRAKEN_ASSETS:
        base_asset_str = pair[0:3]
        quote_asset_str = pair[3:]
    elif pair[0:4] in KRAKEN_ASSETS:
        base_asset_str = pair[0:4]
        quote_asset_str = pair[4:]
    else:
        raise UnprocessableTradePair(pair)

    base_asset = asset_from_kraken(base_asset_str)
    quote_asset = asset_from_kraken(quote_asset_str)

    return trade_pair_from_assets(base_asset, quote_asset)


def world_to_kraken_pair(tradeable_pairs: List[str], pair: TradePair) -> str:
    base_asset, quote_asset = pair_get_assets(pair)

    base_asset_str = base_asset.to_kraken()
    quote_asset_str = quote_asset.to_kraken()

    pair1 = base_asset_str + quote_asset_str
    pair2 = quote_asset_str + base_asset_str

    # In some pairs, XXBT is XBT and ZEUR is EUR ...
    pair3 = None
    if 'XXBT' in pair1:
        pair3 = pair1.replace('XXBT', 'XBT')
    pair4 = None
    if 'XXBT' in pair2:
        pair4 = pair2.replace('XXBT', 'XBT')
    if 'ZEUR' in pair1:
        pair3 = pair1.replace('ZEUR', 'EUR')
    pair4 = None
    if 'ZEUR' in pair2:
        pair4 = pair2.replace('ZEUR', 'EUR')

    if pair1 in tradeable_pairs:
        new_pair = pair1
    elif pair2 in tradeable_pairs:
        new_pair = pair2
    elif pair3 in tradeable_pairs:
        new_pair = pair3
    elif pair4 in tradeable_pairs:
        new_pair = pair4
    else:
        raise ValueError(
            f'Unknown pair "{pair}" provided. Couldnt find {base_asset_str + quote_asset_str}'
            f' or {quote_asset_str + base_asset_str} in tradeable pairs',
        )

    return new_pair


def trade_from_kraken(kraken_trade: Dict[str, Any]) -> Trade:
    """Turn a kraken trade returned from kraken trade history to our common trade
    history format

    - Can raise UnknownAsset due to kraken_to_world_pair
    - Can raise UnprocessableTradePair due to kraken_to_world_pair
    - Can raise DeserializationError due to dict entries not being as expected
    - Can raise KeyError due to dict entries missing an expected entry
    """
    currency_pair = kraken_to_world_pair(kraken_trade['pair'])
    quote_currency = get_pair_position_asset(currency_pair, 'second')

    timestamp = deserialize_timestamp_from_kraken(kraken_trade['time'])
    amount = deserialize_asset_amount(kraken_trade['vol'])
    cost = deserialize_price(kraken_trade['cost'])
    fee = deserialize_fee(kraken_trade['fee'])
    order_type = deserialize_trade_type(kraken_trade['type'])
    rate = deserialize_price(kraken_trade['price'])

    if cost != amount * rate:
        log.warning(f'cost ({cost}) != amount ({amount}) * rate ({rate}) for kraken trade')

    log.debug(
        'Processing kraken Trade',
        sensitive_log=True,
        timestamp=timestamp,
        order_type=order_type,
        kraken_pair=kraken_trade['pair'],
        pair=currency_pair,
        quote_currency=quote_currency,
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
        pair=currency_pair,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=quote_currency,
        link=exchange_uuid,
    )


def _check_and_get_response(response: Response, method: str) -> dict:
    """Checks the kraken response and if it's succesfull returns the result. If there
    is an error an exception is raised"""
    if response.status_code in (520, 525, 504):
        raise RecoverableRequestError('kraken', 'Usual kraken 5xx shenanigans')
    elif response.status_code != 200:
        raise RemoteError(
            'Kraken API request {} for {} failed with HTTP status '
            'code: {}'.format(
                response.url,
                method,
                response.status_code,
            ))

    result = rlk_jsonloads_dict(response.text)
    if result['error']:
        if isinstance(result['error'], list):
            error = result['error'][0]
        else:
            error = result['error']

        if 'Rate limit exceeded' in error:
            raise RecoverableRequestError('kraken', 'Rate limited exceeded')
        else:
            raise RemoteError(error)

    return result['result']


class Kraken(ExchangeInterface):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ):
        super(Kraken, self).__init__('kraken', api_key, secret, database)
        self.msg_aggregator = msg_aggregator
        self.session.headers.update({
            'API-Key': self.api_key,  # type: ignore
        })

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
            self.query_private(method_str, req)
        except (RemoteError, ValueError) as e:
            error = str(e)
            if 'Error: Incorrect padding' in error:
                return False, 'Provided API Key or secret is in invalid Format'
            elif 'EAPI:Invalid key' in error:
                return False, 'Provided API Key is invalid'
            elif 'EGeneral:Permission denied' in error:
                msg = (
                    'Provided API Key does not have appropriate permissions. Make '
                    'sure that the "Query Funds", "Query Open/Closed Order and Trades"'
                    'and "Query Ledger Entries" actions are allowed for your Kraken API Key.'
                )
                return False, msg
            else:
                log.error(f'Kraken API key validation error: {str(e)}')
                msg = (
                    'Unknown error at Kraken API key validation. Perhaps API '
                    'Key/Secret combination invalid?'
                )
                return False, msg
        return True, ''

    def first_connection(self) -> None:
        self.first_connection_made = True

    def _query_public(self, method: str, req: Optional[dict] = None) -> dict:
        """API queries that do not require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})
        """
        if req is None:
            req = {}
        urlpath = f'{KRAKEN_BASE_URL}/{KRAKEN_API_VERSION}/public/{method}'
        log.debug('Kraken Public API query', request_url=urlpath, data=req)
        response = self.session.post(urlpath, data=req)
        return _check_and_get_response(response, method)

    def query_public(self, method: str, req: Optional[dict] = None) -> dict:
        return retry_calls(
            times=5, location='kraken',
            handle_429=False,
            backoff_in_seconds=0,
            method_name=method,
            function=self._query_public,
            # function's arguments
            method=method,
            req=req,
        )

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        return retry_calls(
            times=5, location='kraken',
            handle_429=False,
            backoff_in_seconds=0,
            method_name=method,
            function=self._query_private,
            # function's arguments
            method=method,
            req=req,
        )

    def _query_private(self, method: str, req: Optional[dict] = None) -> dict:
        """API queries that require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})

        """
        if req is None:
            req = {}

        urlpath = '/' + KRAKEN_API_VERSION + '/private/' + method

        with self.lock:
            # Protect this section, or else
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
            log.debug('Kraken Private API query', request_url=urlpath, data=post_data)
            response = self.session.post(
                KRAKEN_BASE_URL + urlpath,
                data=post_data.encode(),
            )

        return _check_and_get_response(response, method)

    # ---- General exchanges interface ----
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:
        try:
            old_balances = self.query_private('Balance', req={})

        except RemoteError as e:
            msg = (
                'Kraken API request failed. Could not reach kraken due '
                'to {}'.format(e)
            )
            log.error(msg)
            return None, msg

        balances = dict()
        for k, v in old_balances.items():
            v = FVal(v)
            if v == FVal(0):
                continue

            try:
                our_asset = asset_from_kraken(k)
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found unsupported/unknown kraken asset {e.asset_name}. '
                    f' Ignoring its balance query.',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Found kraken asset with non-string type {type(k)}. '
                    f' Ignoring its balance query.',
                )
                continue

            entry = {}
            entry['amount'] = v
            usd_price = Inquirer().find_usd_price(our_asset)
            entry['usd_value'] = FVal(v * usd_price)

            balances[our_asset] = entry
            log.debug(
                'kraken balance query result',
                sensitive_log=True,
                currency=our_asset,
                amount=entry['amount'],
                usd_value=entry['usd_value'],
            )

        return balances, ''

    def query_until_finished(
            self,
            endpoint: str,
            keyname: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            extra_dict: Optional[dict] = None,
    ) -> List:
        """ Abstracting away the functionality of querying a kraken endpoint where
        you need to check the 'count' of the returned results and provide sufficient
        calls with enough offset to gather all the data of your query.
        """
        result: List = list()

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
            response = self._query_endpoint_for_period(
                endpoint=endpoint,
                start_ts=start_ts,
                end_ts=end_ts,
                offset=offset,
                extra_dict=extra_dict,
            )
            assert count == response['count']
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
                break

            result.extend(response[keyname].values())

        return result

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        result = self.query_until_finished('TradesHistory', 'trades', start_ts, end_ts)

        # And now turn it from kraken trade to our own trade format
        trades = []
        for raw_data in result:
            try:
                trades.append(trade_from_kraken(raw_data))
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

        return trades

    def _query_endpoint_for_period(
            self,
            endpoint: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            offset: Optional[int] = None,
            extra_dict: Optional[dict] = None,
    ) -> dict:
        request: Dict[str, Union[Timestamp, int]] = dict()
        request['start'] = start_ts
        request['end'] = end_ts
        if offset is not None:
            request['ofs'] = offset
        if extra_dict is not None:
            request.update(extra_dict)
        result = self.query_private(endpoint, request)
        return result

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        result = self.query_until_finished(
            endpoint='Ledgers',
            keyname='ledger',
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict=dict(type='deposit'),
        )
        result.extend(self.query_until_finished(
            endpoint='Ledgers',
            keyname='ledger',
            start_ts=start_ts,
            end_ts=end_ts,
            extra_dict=dict(type='withdrawal'),
        ))

        log.debug('Kraken deposit/withdrawals query result', num_results=len(result))

        movements = list()
        for movement in result:
            try:
                asset = asset_from_kraken(movement['asset'])
                movements.append(AssetMovement(
                    location=Location.KRAKEN,
                    category=deserialize_asset_movement_category(movement['type']),
                    timestamp=deserialize_timestamp_from_kraken(movement['time']),
                    asset=asset,
                    amount=deserialize_asset_amount(movement['amount']),
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
