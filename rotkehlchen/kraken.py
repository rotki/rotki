#!/usr/bin/env python
#
# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/clikraken
import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from requests import Response

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_kraken
from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS, KRAKEN_API_VERSION, KRAKEN_BASE_URL
from rotkehlchen.errors import RecoverableRequestError, RemoteError
from rotkehlchen.exchange import Exchange
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import query_cryptocompare_for_fiat_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.order_formatting import (
    AssetMovement,
    Trade,
    get_pair_position_asset,
    pair_get_assets,
    trade_type_from_string,
)
from rotkehlchen.typing import ApiKey, ApiSecret, FilePath, Timestamp, TradePair
from rotkehlchen.utils.misc import cache_response_timewise, convert_to_int, retry_calls
from rotkehlchen.utils.serialization import rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


KRAKEN_ASSETS = (
    'ATOM',
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
    'DASH',
    'EOS',
    'USDT',
    'KFEE',
    'ADA',
    'QTUM',
    'XNMC',
    'XXVN',
    'XXDG',
    'XTZ',
)

KRAKEN_DELISTED = ('XDAO', 'XXVN', 'ZKRW', 'XNMC', 'BSV', 'XICN')


def kraken_to_world_pair(pair: str) -> TradePair:
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
        raise ValueError(f'Could not process kraken trade pair {pair}')

    base_asset = asset_from_kraken(base_asset_str)
    quote_asset = asset_from_kraken(quote_asset_str)

    return TradePair(f'{base_asset}_{quote_asset}')


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
    history format"""
    currency_pair = kraken_to_world_pair(kraken_trade['pair'])
    quote_currency = get_pair_position_asset(currency_pair, 'second')
    # Kraken timestamps have floating point
    timestamp = Timestamp(convert_to_int(kraken_trade['time'], accept_only_exact=False))
    amount = FVal(kraken_trade['vol'])
    cost = FVal(kraken_trade['cost'])
    fee = FVal(kraken_trade['fee'])
    order_type = trade_type_from_string(kraken_trade['type'])
    rate = FVal(kraken_trade['price'])

    if cost != amount * rate:
        log.warning('cost ({cost}) != amount ({amount}) * rate ({rate}) for kraken trade')

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

    return Trade(
        timestamp=timestamp,
        location='kraken',
        pair=currency_pair,
        trade_type=order_type,
        amount=amount,
        rate=rate,
        fee=fee,
        fee_currency=quote_currency,
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


class Kraken(Exchange):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            user_directory: FilePath,
            usd_eur_price: FVal,
    ):
        super(Kraken, self).__init__('kraken', api_key, secret, user_directory)
        # typing TODO: Without a union of str and Asset we get lots of warning
        # How can this be avoided without too much pain?
        self.usdprice: Dict[Union[Asset, str], FVal] = {}
        self.eurprice: Dict[Union[Asset, str], FVal] = {}

        self.usdprice['EUR'] = usd_eur_price
        self.session.headers.update({  # type: ignore
            'API-Key': self.api_key,
        })

    def first_connection(self):
        if self.first_connection_made:
            return

        with self.lock:
            self.tradeable_pairs = self.query_public('AssetPairs')
            # also make sure to get fiat prices from ticker before considering
            # kraken ready for external queries
            self.get_fiat_prices_from_ticker()
            self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self.query_private('Balance', req={})
        except (RemoteError, ValueError) as e:
            error = str(e)
            if 'Error: Incorrect padding' in error:
                return False, 'Provided API Key or secret is in invalid Format'
            elif 'EAPI:Invalid key' in error:
                return False, 'Provided API Key is invalid'
            else:
                raise
        return True, ''

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
        return retry_calls(5, 'kraken', method, self._query_public, method, req)

    def query_private(self, method: str, req: Optional[dict] = None) -> dict:
        return retry_calls(5, 'kraken', method, self._query_private, method, req)

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
            self.session.headers.update({  # type: ignore
                'API-Sign': base64.b64encode(signature.digest()),
            })
            log.debug('Kraken Private API query', request_url=urlpath, data=post_data)
            response = self.session.post(
                KRAKEN_BASE_URL + urlpath,
                data=post_data.encode(),
            )

        return _check_and_get_response(response, method)

    def get_fiat_prices_from_ticker(self):
        self.ticker = self.query_public(
            'Ticker',
            req={'pair': ','.join(self.tradeable_pairs.keys())},
        )
        self.eurprice['BTC'] = FVal(self.ticker['XXBTZEUR']['c'][0])
        self.usdprice['BTC'] = FVal(self.ticker['XXBTZUSD']['c'][0])
        self.eurprice['ETH'] = FVal(self.ticker['XETHZEUR']['c'][0])
        self.usdprice['ETH'] = FVal(self.ticker['XETHZUSD']['c'][0])
        self.eurprice['REP'] = FVal(self.ticker['XREPZEUR']['c'][0])
        self.eurprice['XMR'] = FVal(self.ticker['XXMRZEUR']['c'][0])
        self.usdprice['XMR'] = FVal(self.ticker['XXMRZUSD']['c'][0])
        self.eurprice['ETC'] = FVal(self.ticker['XETCZEUR']['c'][0])
        self.usdprice['ETC'] = FVal(self.ticker['XETCZUSD']['c'][0])

    # ---- General exchanges interface ----
    def main_logic(self):
        if not self.first_connection_made:
            return
        self.get_fiat_prices_from_ticker()

    def find_fiat_price(self, kraken_asset: str) -> FVal:
        """Find USD/EUR price of asset. The asset should be in the kraken style.
        e.g.: XICN. Save both prices in the kraken object and then return the
        USD price.
        """
        if kraken_asset == 'KFEE':
            # Kraken fees have no value
            return FVal(0)

        if kraken_asset == 'XXBT':
            return self.usdprice['BTC']

        if kraken_asset == 'USDT':
            price = FVal(self.ticker['USDTZUSD']['c'][0])
            self.usdprice['USDT'] = price
            return price

        if kraken_asset == 'BSV':
            # BSV has been delisted by kraken at 29/04/19
            # https://blog.kraken.com/post/2274/kraken-is-delisting-bsv/
            # Until May 31st there can be BSV in Kraken (even with 0 balance)
            # so keep this until then to get the price
            return query_cryptocompare_for_fiat_price('BSV')

        # TODO: This is pretty ugly. Find a better way to check out kraken pairs
        # without this ugliness.
        pair = kraken_asset + 'XXBT'
        pair2 = kraken_asset + 'XBT'
        pair3 = 'XXBT' + kraken_asset
        inverse = False
        if pair2 in self.tradeable_pairs:
            pair = pair2
        elif pair3 in self.tradeable_pairs:
            pair = pair3
            # here XXBT is the base asset so inverse
            inverse = True

        if pair not in self.tradeable_pairs:
            raise ValueError(
                'Could not find a BTC tradeable pair in kraken for "{}"'.format(kraken_asset),
            )
        btc_price = FVal(self.ticker[pair]['c'][0])
        if inverse:
            btc_price = FVal('1.0') / btc_price
        our_asset = asset_from_kraken(kraken_asset)
        with self.lock:
            self.usdprice[our_asset] = btc_price * self.usdprice['BTC']
            self.eurprice[our_asset] = btc_price * self.eurprice['BTC']
        return self.usdprice[our_asset]

    @cache_response_timewise(CACHE_RESPONSE_FOR_SECS)
    def query_balances(self) -> Tuple[Optional[dict], str]:
        try:
            self.first_connection()
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

            our_asset = asset_from_kraken(k)
            entry = {}
            entry['amount'] = v
            if our_asset in self.usdprice:
                entry['usd_value'] = v * self.usdprice[our_asset]
            else:
                entry['usd_value'] = v * self.find_fiat_price(k)

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
                # https://github.com/rotkehlchenio/rotkehlchen/issues/116
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

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> List:
        with self.lock:
            cache = self.check_trades_cache(start_ts, end_at_least_ts)
            cache = cast(List, cache)

        if cache is not None:
            return cache
        result = self.query_until_finished('TradesHistory', 'trades', start_ts, end_ts)

        with self.lock:
            # before returning save it in the disk for future reference
            self.update_trades_cache(result, start_ts, end_ts)
        return result

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

    def query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> List:
        with self.lock:
            cache = self.check_trades_cache(
                start_ts,
                end_at_least_ts,
                special_name='deposits_withdrawals',
            )

        if cache is not None:
            result = cache
        else:
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

            with self.lock:
                self.update_trades_cache(
                    result,
                    start_ts,
                    end_ts,
                    special_name='deposits_withdrawals',
                )

        log.debug('Kraken deposit/withdrawals query result', num_results=len(result))

        movements = list()
        for movement in result:
            movements.append(AssetMovement(
                exchange='kraken',
                category=movement['type'],
                # Kraken timestamps have floating point
                timestamp=convert_to_int(movement['time'], accept_only_exact=False),
                asset=asset_from_kraken(movement['asset']),
                amount=FVal(movement['amount']),
                fee=FVal(movement['fee']),
            ))

        return movements
