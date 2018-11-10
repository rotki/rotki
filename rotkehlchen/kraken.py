#!/usr/bin/env python
#
# Good kraken and python resource:
# https://github.com/zertrin/clikraken/tree/master/clikraken
import base64
import hashlib
import hmac
import logging
import time
from typing import Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from requests import Response

from rotkehlchen import typing
from rotkehlchen.errors import RecoverableRequestError, RemoteError
from rotkehlchen.exchange import Exchange
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import query_cryptocompare_for_fiat_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.order_formatting import AssetMovement, Trade
from rotkehlchen.utils import (
    cache_response_timewise,
    convert_to_int,
    get_pair_position,
    query_fiat_pair,
    retry_calls,
    rlk_jsonloads,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KRAKEN_TO_WORLD = {
    'XDAO': 'DAO',
    'XETC': 'ETC',
    'XETH': 'ETH',
    'XLTC': 'LTC',
    'XREP': 'REP',
    'XXBT': 'BTC',
    'XBT': 'BTC',
    'XXMR': 'XMR',
    'XXRP': 'XRP',
    'XZEC': 'ZEC',
    'ZEUR': 'EUR',
    'ZUSD': 'USD',
    'ZGBP': 'GBP',
    'ZCAD': 'CAD',
    'ZJPY': 'JPY',
    'ZKRW': 'KRW',
    'XMLN': 'MLN',
    'XICN': 'ICN',
    'GNO': 'GNO',
    'BCH': 'BCH',
    'XXLM': 'XLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'USDT': 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'XNMC': 'NMC',
    'XXVN': 'XVN',
    'XXDG': 'XDG',
    'XTZ': 'XTZ',
}

WORLD_TO_KRAKEN = {
    'ETC': 'XETC',
    'ETH': 'XETH',
    'LTC': 'XLTC',
    'REP': 'XREP',
    'BTC': 'XXBT',
    'XMR': 'XXMR',
    'XRP': 'XXRP',
    'ZEC': 'XZEC',
    'EUR': 'ZEUR',
    'USD': 'ZUSD',
    'GBP': 'ZGBP',
    'CAD': 'ZCAD',
    'JPY': 'ZJPY',
    'KRW': 'ZKRW',
    'DAO': 'XDAO',
    'MLN': 'XMLN',
    'ICN': 'XICN',
    'GNO': 'GNO',
    'BCH': 'BCH',
    'XLM': 'XXLM',
    'DASH': 'DASH',
    'EOS': 'EOS',
    'USDT': 'USDT',
    'KFEE': 'KFEE',
    'ADA': 'ADA',
    'QTUM': 'QTUM',
    'NMC': 'XNMC',
    'XVN': 'XXVN',
    'XDG': 'XXDG',
    'XTZ': 'XTZ',
}

KRAKEN_ASSETS = (
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

KRAKEN_DELISTED = ('XDAO', 'XXVN', 'ZKRW', 'XNMC')


def kraken_to_world_pair(pair):
    # handle dark pool pairs
    if pair[-2:] == '.d':
        pair = pair[:-2]

    if pair[0:3] in KRAKEN_ASSETS:
        base_currency = pair[0:3]
        quote_currency = pair[3:]
    elif pair[0:4] in KRAKEN_ASSETS:
        base_currency = pair[0:4]
        quote_currency = pair[4:]
    else:
        raise ValueError(f'Could not process kraken trade pair {pair}')

    if base_currency not in WORLD_TO_KRAKEN:
        base_currency = KRAKEN_TO_WORLD[base_currency]
    if quote_currency not in WORLD_TO_KRAKEN:
        quote_currency = KRAKEN_TO_WORLD[quote_currency]

    return base_currency + '_' + quote_currency


def trade_from_kraken(kraken_trade):
    """Turn a kraken trade returned from kraken trade history to our common trade
    history format"""
    currency_pair = kraken_to_world_pair(kraken_trade['pair'])
    quote_currency = get_pair_position(currency_pair, 'second')
    # Kraken timestamps have floating point
    timestamp = convert_to_int(kraken_trade['time'], accept_only_exact=False)
    amount = FVal(kraken_trade['vol'])
    cost = FVal(kraken_trade['cost'])
    fee = FVal(kraken_trade['fee'])
    order_type = kraken_trade['type']
    rate = FVal(kraken_trade['price'])

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
        pair=currency_pair,
        type=order_type,
        rate=rate,
        cost=cost,
        cost_currency=quote_currency,
        fee=fee,
        fee_currency=quote_currency,
        amount=amount,
        location='kraken'
    )


class Kraken(Exchange):
    def __init__(
            self,
            api_key: typing.ApiKey,
            secret: typing.ApiSecret,
            data_dir: typing.FilePath,
    ):
        super(Kraken, self).__init__('kraken', api_key, secret, data_dir)
        self.apiversion = '0'
        self.uri = 'https://api.kraken.com/{}/'.format(self.apiversion)
        # typing TODO: Without a union of str and Asset we get lots of warning
        # How can this be avoided without too much pain?
        self.usdprice: Dict[Union[typing.Asset, str], FVal] = {}
        self.eurprice: Dict[Union[typing.Asset, str], FVal] = {}
        self.session.headers.update({
            'API-Key': self.api_key,
        })

    def first_connection(self):
        if self.first_connection_made:
            return

        resp = self.query_private(
            'TradeVolume',
            req={'pair': 'XETHXXBT', 'fee-info': True}
        )
        with self.lock:
            # Assuming all fees are the same for all pairs that we trade here,
            # as long as they are normal orders on normal pairs.

            self.taker_fee = FVal(resp['fees']['XETHXXBT']['fee'])
            # Note from kraken api: If an asset pair is on a maker/taker fee
            # schedule, the taker side is given in "fees" and maker side in
            # "fees_maker". For pairs not on maker/taker, they will only be
            # given in "fees".
            if 'fees_maker' in resp:
                self.maker_fee = FVal(resp['fees_maker']['XETHXXBT']['fee'])
            else:
                self.maker_fee = self.taker_fee
            self.tradeable_pairs = self.query_public('AssetPairs')
            self.first_connection_made = True

        # Also need to do at least a single pass of the main logic for the ticker
        self.main_logic()

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

    def check_and_get_response(self, response: Response, method: str) -> dict:
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

        result = rlk_jsonloads(response.text)
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

    def _query_public(self, method: str, req: Optional[dict] = None) -> dict:
        """API queries that do not require a valid key/secret pair.

        Arguments:
        method -- API method name (string, no default)
        req    -- additional API request parameters (default: {})
        """
        if req is None:
            req = {}
        urlpath = self.uri + 'public/' + method
        log.debug('Kraken Public API query', request_url=urlpath, data=req)
        response = self.session.post(urlpath, data=req)
        return self.check_and_get_response(response, method)

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

        urlpath = '/' + self.apiversion + '/private/' + method

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
                hashlib.sha512
            )
            self.session.headers.update({
                'API-Sign': base64.b64encode(signature.digest())
            })
            log.debug('Kraken Private API query', request_url=urlpath, data=post_data)
            response = self.session.post(
                'https://api.kraken.com' + urlpath,
                data=post_data.encode()
            )

        return self.check_and_get_response(response, method)

    def world_to_kraken_pair(self, pair: str) -> str:
        p1, p2 = pair.split('_')
        kraken_p1 = WORLD_TO_KRAKEN[p1]
        kraken_p2 = WORLD_TO_KRAKEN[p2]
        if kraken_p1 + kraken_p2 in self.tradeable_pairs:
            pair = kraken_p1 + kraken_p2
        elif kraken_p2 + kraken_p1 in self.tradeable_pairs:
            pair = kraken_p2 + kraken_p1
        else:
            raise ValueError('Unknown pair "{}" provided'.format(pair))
        return pair

    def get_fiat_prices_from_ticker(self):
        self.ticker = self.query_public(
            'Ticker',
            req={'pair': ','.join(self.tradeable_pairs.keys())}
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

    def find_fiat_price(self, asset: typing.Asset) -> FVal:
        """Find USD/EUR price of asset. The asset should be in the kraken style.
        e.g.: XICN. Save both prices in the kraken object and then return the
        USD price.
        """
        if asset == 'KFEE':
            # Kraken fees have no value
            return FVal(0)

        if asset == 'XXBT':
            return self.usdprice['BTC']

        if asset == 'USDT':
            price = FVal(self.ticker['USDTZUSD']['c'][0])
            self.usdprice['USDT'] = price
            return price

        if asset == 'XICN':
            # ICN has been delisted by kraken at 31/10/2018 and withdrawals
            # will only last until 31/11/2018. For this period of time there
            # can be ICN in Kraken -- so use crypto compare for price info
            return query_cryptocompare_for_fiat_price(typing.EthToken('ICN'))

        # TODO: This is pretty ugly. Find a better way to check out kraken pairs
        # without this ugliness.
        pair = asset + 'XXBT'
        pair2 = asset + 'XBT'
        pair3 = 'XXBT' + asset
        if pair2 in self.tradeable_pairs:
            pair = pair2
        elif pair3 in self.tradeable_pairs:
            pair = pair3

        if pair not in self.tradeable_pairs:
            raise ValueError(
                'Could not find a BTC tradeable pair in kraken for "{}"'.format(asset)
            )
        btc_price = FVal(self.ticker[pair]['c'][0])
        common_name = KRAKEN_TO_WORLD[asset]
        with self.lock:
            self.usdprice[common_name] = btc_price * self.usdprice['BTC']
            self.eurprice[common_name] = btc_price * self.eurprice['BTC']
        return self.usdprice[common_name]

    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:
        try:
            self.first_connection()
            old_balances = self.query_private('Balance', req={})
            # find USD price of EUR
            with self.lock:
                self.usdprice['EUR'] = query_fiat_pair('EUR', 'USD')

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

            common_name = KRAKEN_TO_WORLD[k]
            entry = {}
            entry['amount'] = v
            if common_name in self.usdprice:
                entry['usd_value'] = v * self.usdprice[common_name]
            else:
                entry['usd_value'] = v * self.find_fiat_price(k)

            balances[common_name] = entry
            log.debug(
                'kraken balance query result',
                sensitive_log=True,
                currency=common_name,
                amount=entry['amount'],
                usd_value=entry['usd_value'],
            )

        return balances, ''

    def query_until_finished(
            self,
            endpoint: str,
            keyname: str,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
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
            extra_dict=extra_dict
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
                extra_dict=extra_dict
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
                        count - offset, endpoint)
                )
                break

            result.extend(response[keyname].values())

        return result

    def query_trade_history(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
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
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            offset: Optional[int] = None,
            extra_dict: Optional[dict] = None,
    ) -> dict:
        request: Dict[str, Union[typing.Timestamp, int]] = dict()
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
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
    ) -> List:
        with self.lock:
            cache = self.check_trades_cache(
                start_ts,
                end_at_least_ts,
                special_name='deposits_withdrawals'
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
                    special_name='deposits_withdrawals'
                )

        log.debug('Kraken deposit/withdrawals query result', num_results=len(result))

        movements = list()
        for movement in result:
            movements.append(AssetMovement(
                exchange='kraken',
                category=movement['type'],
                # Kraken timestamps have floating point
                timestamp=convert_to_int(movement['time'], accept_only_exact=False),
                asset=KRAKEN_TO_WORLD[movement['asset']],
                amount=FVal(movement['amount']),
                fee=FVal(movement['fee'])
            ))

        return movements
