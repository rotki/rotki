#!/usr/bin/env python
import time
import hmac
import hashlib
import datetime
import os
import traceback
import csv
from urllib.parse import urlencode
from typing import Tuple, Dict, Optional, List, Union, cast
import bitmex

from rotkehlchen.fval import FVal
from rotkehlchen.utils import (
    createTimeStamp,
    retry_calls,
    rlk_jsonloads,
    cache_response_timewise,
)
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.exchange import Exchange
from rotkehlchen.order_formatting import AssetMovement
from rotkehlchen.errors import BitmexError, RemoteError
from rotkehlchen import typing

import logging
logger = logging.getLogger(__name__)


def tsToDate(s):
    return datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')


class Bitmex(Exchange):

    def __init__(
            self,
            api_key,
            secret,
            inquirer: Inquirer,
            data_dir: typing.FilePath,
    ):
        super(Bitmex, self).__init__('bitmex', str.encode(api_key), str.encode(secret), data_dir)


        self.client = None
        self.api_key = api_key
        self.secret = secret
        self.usdprice: Dict[typing.BlockchainAsset, FVal] = {}
        self.inquirer = inquirer
        self.session.headers.update({
            'Key': self.api_key,
        })

    def first_connection(self):
        if self.first_connection_made:
            return

        #fees_resp = self.returnFeeInfo()
        with self.lock:
            self.maker_fee = FVal(-0.00025)
            self.taker_fee = FVal(0.00075)
            self.first_connection_made = True
        # Also need to do at least a single pass of the market watcher for the ticker
        self.market_watcher()

    def validate_api_key(self) -> Tuple[bool, str]:

        if self.client == None:
            self.client = bitmex.bitmex(test=False,api_key=self.api_key,api_secret=self.secret)
        try:
            self.api_query('returnUserInfo')
        except:
            raise BitmexError('Provided API Key or secret is invalid')

        return True, ''

    def post_process(self, before: Dict) -> Dict:
        after = before

        # Add timestamps if there isnt one but is a datetime
        if('return' in after):
            if(isinstance(after['return'], list)):
                for x in range(0, len(after['return'])):
                    if(isinstance(after['return'][x], dict)):
                        if('datetime' in after['return'][x] and
                           'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(
                                createTimeStamp(after['return'][x]['datetime'])
                            )

        return after

    def api_query(self, command: str, req: Optional[Dict] = None) -> Dict:
        result = retry_calls(5, 'bitmex', command, self._api_query, command, req)
        if 'error' in result:
            raise BitmexError(
                'Bitmex query for "{}" returned error: {}'.format(
                    command,
                    result['error']
                ))
        return result

    def _api_query(self, command: str, req: Optional[Dict] = None) -> Dict:
        if command == "returnTicker":
            ret = self.client.Instrument.Instrument_get(filter=json.dumps({'symbol': req['symbol']})).result()[0][0]
        if command == 'returnFeeInfo':
            print("todo")
            # it does not work
            # ret = self.client.User.User_getCommission().result()
        if command == 'returnUserInfo':
            ret = self.client.User.User_get().result()[0]
        if command == 'returnCompleteBalances':
            ret = self.client.User.User_getWallet(currency='XBt').result()[0]
        if command == 'returnOrderBook':
            ret = self.client.OrderBook.OrderBook_getL2(symbol=req['symbol'], depth=20).result()[0]
        if command == 'returnLandingHistory':
            ret = self.client.User.User_getWalletHistory(currency='XBt').result()[0]
        if command == 'returnMarketTradeHistory':
            print("todo")
            #it seems there is no markettradehistory api call
        if command == 'returnDepositsWithdrawals':
            print("todo")
            # I can't test it
        if command == 'returnOpenOrders':
            ret = self.client.Order.Order_getOrders(filter=json.dumps({'open':True})).result()[0]
            
        return ret


    def returnTicker(self,currencypair: typing.BlockchainAsset) -> Dict:
        return self.api_query("returnTicker",{'symbol':currencypair})


    def returnOrderBook(sedl,currencypair:typing.BlockchainAsset) -> Dict:
        return self.api_query("returnOrderBook",{'symbol':currencypair})

    def returnFeeInfo(self) -> Dict:
        return self.api_query("returnFeeInfo")

    def returnUserInfo(self) -> Dict:
        return self.api_query("returnUserInfo")

    def returnLendingHistory(
            self,
            start_ts: Optional[typing.Timestamp] = None,
            end_ts: Optional[typing.Timestamp] = None,
            limit: Optional[int] = None,
    ) -> Dict:
        """Default limit for this endpoint seems to be 500 when I tried.
        So to be sure all your loans are included put a very high limit per call
        and also check if the limit was reached after each call.

        Also maximum limit seems to be 12660
        """
        req: Dict[str, Union[int, typing.Timestamp]] = dict()
        if start_ts is not None:
            req['start'] = start_ts
        if end_ts is not None:
            req['end'] = end_ts
        if limit is not None:
            req['limit'] = limit
        return self.api_query("returnLendingHistory", req)

    def returnMarketTradeHistory(self, currencyPair: str) -> Dict:
        return self.api_query(
            "returnMarketTradeHistory",
            {'currencyPair': currencyPair}
        )


    # Returns your open orders for a given market,
    # specified by the "currencyPair" POST parameter, e.g. "BTCUSD"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTCUSD"
    # Outputs:
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self, currencyPair: str) -> Dict:
        return self.api_query(
            'returnOpenOrders',
            {"currencyPair": currencyPair}
        )

    def returnTradeHistory(
            self,
            currencyPair: str,
            start: typing.Timestamp,
            end: typing.Timestamp,
    ) -> Union[Dict, List]:
        """If `currencyPair` is all, then it returns a dictionary with each key
        being a pair and each value a list of trades. If `currencyPair` is a specific
        pair then a list is returned"""
        return self.api_query('returnMarketTradeHistory', {
            "currencyPair": currencyPair,
            'start': start,
            'end': end,
            'limit': 10000,
        })

    def returnDepositsWithdrawals(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
    ) -> Dict:
        return self.api_query('returnDepositsWithdrawals', {'start': start_ts, 'end': end_ts})

    def market_watcher(self):
        with self.lock:
            self.usdprice['BTC'] = Fval(self.returnTicker('XBTUSD')['lastPrice'])
            self.usdprice['ETH'] = FVal(self.returnTicker('ETHUSD')['lastPrice'])
            self.usdprice['ADA'] = FVal(self.returnTicker('.ADAXBT')['lastPrice']) * self.usdprice['BTC']
            self.usdprice['BCH'] = FVal(self.returnTicker('.BCHXBT')['lastPrice']) * self.usdprice['BTC']
            self.usdprice['LTC'] = FVal(self.returnTicker('.LTCXBT')['lastPrice']) * self.usdprice['BTC']
            self.usdprice['EOS'] = FVal(self.returnTicker('.EOSXBT')['lastPrice']) * self.usdprice['BTC']
            self.usdprice['TRX'] = FVal(self.returnTicker('.TRXXBT')['lastPrice']) * self.usdprice['BTC']
            self.usdprice['XRP'] = Fval(self.returnTicker('.XRPXBT')['lastPrice']) * self.usdprice['BTC']

    def main_logic(self):
        if not self.first_connection_made:
            return

        try:
            self.market_watcher()

        except BitmexError as e:
            logger.error("Bitmex error at main loop: {}".format(str(e)))
        except Exception as e:
            logger.error(
                "\nException at main loop: {}\n{}\n".format(
                    str(e), traceback.format_exc())
            )

    # ---- General exchanges interface ----
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:
        if self.client == None:
            self.client = bitmex.bitmex(test=False,api_key=self.api_key,api_secret=self.secret)
        try:
            resp = self.api_query('returnCompleteBalances')
        except:
            msg = ('Bitmex API request failed. Could not reach bitmex')
            logger.error(msg)
            return None, msg

        balances = dict()
        available = FVal(resp['amount'])
        on_orders = FVal(0)
        entry = {}
        entry['amount'] = available + on_orders
        usd_price = self.inquirer.find_usd_price(
            asset="BTC",
            asset_btc_price=None
        )
        usd_value = entry['amount'] * usd_price
        entry['usd_value'] = usd_value
        balances["BTC"] = entry
        return balances,''

    def query_trade_history(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
    ) -> Union[List, Dict]:
        with self.lock:
            cache = self.check_trades_cache(start_ts, end_at_least_ts)
        if cache is not None:
            return cache

        result = self.returnTradeHistory(
            currencyPair='all',
            start=start_ts,
            end=end_ts
        )
        # we know that returnTradeHistory returns a dict with currencyPair=all
        result = cast(Dict, result)

        results_length = 0
        for r, v in result.items():
            results_length += len(v)

        if results_length >= 10000:
            raise ValueError(
                'Bitmex api has a 10k limit to trade history. Have not implemented'
                ' a solution for more than 10k trades at the moment'
            )

        with self.lock:
            self.update_trades_cache(result, start_ts, end_ts)
        return result

    def parseLoanCSV(self) -> List:
        """Parses (if existing) the lendingHistory.csv and returns the history in a list

        It can throw OSError, IOError if the file does not exist and csv.Error if
        the file is not proper CSV"""
        # the default filename, and should be (if at all) inside the data directory
        path = os.path.join(self.data_dir, "lendingHistory.csv")
        lending_history = list()
        with open(path, 'r') as csvfile:
            history = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(history)  # skip header row
            for row in history:
                lending_history.append({
                    'currency': row[0],
                    'earned': FVal(row[6]),
                    'amount': FVal(row[2]),
                    'fee': FVal(row[5]),
                    'open': row[7],
                    'close': row[8]
                })
        return lending_history

    def query_loan_history(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
            from_csv: Optional[bool] = False,
    ) -> List:
        """
        WARNING: Querying from returnLendingHistory endpoing instead of reading from
        the CSV file can potentially  return unexpected/wrong results.

        That is because the `returnLendingHistory` endpoint has a hidden limit
        of 12660 results. In our code we use the limit of 12000 but bitmex may change
        the endpoint to have a lower limit at which case this code will break.

        To be safe compare results of both CSV and endpoint to make sure they agree!
        """
        try:
            if from_csv:
                return self.parseLoanCSV()
        except (OSError, IOError, csv.Error):
            pass

        with self.lock:
            # We know Loan history cache is a list
            cache = cast(
                List,
                self.check_trades_cache(start_ts, end_at_least_ts, special_name='loan_history'),
            )
        if cache is not None:
            return cache

        loans_query_return_limit = 12000
        result = self.returnLendingHistory(
            start_ts=start_ts,
            end_ts=end_ts,
            limit=loans_query_return_limit
        )
        data = list(result)

        # since I don't think we have any guarantees about order of results
        # using a set of loan ids is one way to make sure we get no duplicates
        # if bitmex can guarantee me that the order is going to be ascending/descending
        # per open/close time then this can be improved
        id_set = set()

        while len(result) == loans_query_return_limit:
            # Find earliest timestamp to re-query the next batch
            min_ts = end_ts
            for loan in result:
                ts = createTimeStamp(loan['close'], formatstr="%Y-%m-%d %H:%M:%S")
                min_ts = min(min_ts, ts)
                id_set.add(loan['id'])

            result = self.returnLendingHistory(
                start_ts=start_ts,
                end_ts=min_ts,
                limit=loans_query_return_limit
            )
            for loan in result:
                if loan['id'] not in id_set:
                    data.append(loan)

        with self.lock:
            self.update_trades_cache(data, start_ts, end_ts, special_name='loan_history')
        return data

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
            cache = cast(Dict, cache)
        if cache is None:
            result = self.returnDepositsWithdrawals(start_ts, end_ts)
            with self.lock:
                self.update_trades_cache(
                    result,
                    start_ts,
                    end_ts,
                    special_name='deposits_withdrawals'
                )
        else:
            result = cache

        movements = list()
        for withdrawal in result['withdrawals']:
            movements.append(AssetMovement(
                exchange='bitmex',
                category='withdrawal',
                timestamp=withdrawal['timestamp'],
                asset=withdrawal['currency'],
                amount=FVal(withdrawal['amount']),
                fee=FVal(withdrawal['fee'])
            ))

        for deposit in result['deposits']:
            movements.append(AssetMovement(
                exchange='bitmex',
                category='deposit',
                timestamp=deposit['timestamp'],
                asset=deposit['currency'],
                amount=FVal(deposit['amount']),
                fee=0
            ))

        return movements
