#!/usr/bin/env python
import time
import hmac
import hashlib
import datetime
import os
import traceback
import csv
from urllib.parse import urlencode

from rotkehlchen.fval import FVal
from rotkehlchen.utils import (
    createTimeStamp,
    retry_calls,
    rlk_jsonloads,
    cache_response_timewise,
)
from rotkehlchen.exchange import Exchange
from rotkehlchen.order_formatting import AssetMovement
from rotkehlchen.errors import PoloniexError

import logging
logger = logging.getLogger(__name__)


def tsToDate(s):
    return datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')


class WatchedCurrency(object):

    def __init__(self, low, high, threshold):
        self.low = low
        self.high = high
        self.threshold = threshold
        self.last = 0.0
        self.last_percentage = 0.0


class Poloniex(Exchange):

    settings = [
        'watched_currencies'
    ]

    def __init__(self, api_key, secret, cache_filename, inquirer, data_dir):
        super(Poloniex, self).__init__('poloniex', api_key, secret)

        self.uri = 'https://poloniex.com/'
        self.public_uri = self.uri + 'public?command='
        self.cache_filename = cache_filename
        self.data_dir = data_dir
        # Set default setting values
        self.watched_currencies = {
            'BTC_DASH': WatchedCurrency(0.0, 0.5, 0.000500),
            'BTC_XMR': WatchedCurrency(0.0, 0.5, 0.000500),
            'BTC_LBC': WatchedCurrency(0.0, 0.00036084, 0.00000100),
            'BTC_ETH': WatchedCurrency(0.0, 0.5, 0.000500),
            'BTC_LTC': WatchedCurrency(0.0, 0.5, 0.0),
            'BTC_MAID': WatchedCurrency(0.0, 0.5, 0.0),
            'BTC_XRP': WatchedCurrency(0.0, 1.0, 0.0),
            'BTC_DOGE': WatchedCurrency(0.0, 1.0, 0.0),
            'BTC_BTS': WatchedCurrency(0.0, 1.0, 0.0),
            'BTC_CLAM': WatchedCurrency(0.0, 1.0, 0.0),
            'USDT_BTC': WatchedCurrency(0.0, 1000.0, 1.0),
            'ETH_REP': WatchedCurrency(0.0, 0.435, 0.01),
        }
        self.usdprice = {}
        self.inquirer = inquirer
        self.session.headers.update({
            'Key': self.api_key,
        })

    def first_connection(self):
        if self.first_connection_made:
            return

        fees_resp = self.returnFeeInfo()
        with self.lock:
            self.maker_fee = FVal(fees_resp['makerFee'])
            self.taker_fee = FVal(fees_resp['takerFee'])
            self.first_connection_made = True
        # Also need to do at least a single pass of the market watcher for the ticker
        self.market_watcher()

    def validate_api_key(self):
        try:
            self.returnFeeInfo()
        except ValueError as e:
            error = str(e)
            if 'Invalid API key/secret pair' in error:
                return False, 'Provided API Key or secret is invalid'
            else:
                raise
        return True, ''

    def post_process(self, before):
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

    def api_query(self, command, req={}):
        result = retry_calls(5, 'poloniex', command, self._api_query, command, req)
        if 'error' in result:
            raise ValueError(
                'Poloniex query for "{}" returned error: {}'.format(
                    command,
                    result['error']
                ))
        return result

    def _api_query(self, command, req={}):
        if command == "returnTicker" or command == "return24Volume":
            ret = self.session.get(self.public_uri + command)
        elif(command == "returnOrderBook"):
            ret = self.session.get(
                self.public_uri + command +
                '&currencyPair=' + str(req['currencyPair'])
            )
        elif(command == "returnMarketTradeHistory"):
            ret = self.session.get(
                self.public_uri + 'returnTradeHistory' + '&currencyPair=' +
                str(req['currencyPair'])
            )
        elif(command == "returnLoanOrders"):
            ret = self.session.get(
                self.public_uri + 'returnLoanOrders' + '&currency=' +
                str(req['currency'])
            )
        else:
            req['command'] = command

            with self.lock:
                # Protect this region with a lock since poloniex will reject
                # non-increasing nonces. So if two greenlets come in here at
                # the same time one of them will fail
                req['nonce'] = int(time.time() * 1000)
                post_data = str.encode(urlencode(req))

                sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
                self.session.headers.update({'Sign': sign})
                ret = self.session.post('https://poloniex.com/tradingApi', req)

            result = rlk_jsonloads(ret.text)
            return self.post_process(result)

        return rlk_jsonloads(ret.text)

    def returnAvailableAccountBalances(self, account='all'):
        req = {}
        if account:
            req = {'account': account}
        return self.api_query("returnAvailableAccountBalances", req)

    def returnLoanOrders(self, currency):
        return self.api_query('returnLoanOrders', {'currency': currency})

    def returnTicker(self):
        return self.api_query("returnTicker")

    def return24Volume(self):
        return self.api_query("return24Volume")

    def returnFeeInfo(self):
        return self.api_query("returnFeeInfo")

    def returnLendingHistory(self, start_ts=None, end_ts=None, limit=None):
        """Default limit for this endpoint seems to be 500 when I tried.
        So to be sure all your loans are included put a very high limit per call
        and also check if the limit was reached after each call.

        Also maximum limit seems to be 12660
        """
        req = dict()
        if start_ts is not None:
            req['start'] = start_ts
        if end_ts is not None:
            req['end'] = end_ts
        if limit is not None:
            req['limit'] = limit
        return self.api_query("returnLendingHistory", req)

    def returnMarketTradeHistory(self, currencyPair):
        return self.api_query(
            "returnMarketTradeHistory",
            {'currencyPair': currencyPair}
        )

    # Returns all of your balances.
    # Outputs:
    # {"BTC":"0.59098578","LTC":"3.31117268", ... }
    def returnBalances(self):
        return self.api_query('returnBalances')

    # Returns your open orders for a given market,
    # specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self, currencyPair):
        return self.api_query(
            'returnOpenOrders',
            {"currencyPair": currencyPair}
        )

    # Returns your trade history for a given market,
    # specified by the "currencyPair" POST parameter
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # date          Date in the form: "2014-02-19 03:44:59"
    # rate          Price the order is selling or buying at
    # amount        Quantity of order
    # total         Total value of order (price * quantity)
    # type          sell or buy
    def returnTradeHistory(self, currencyPair, start=None, end=None):
        return self.api_query('returnTradeHistory', {
            "currencyPair": currencyPair,
            'start': start,
            'end': end
        })

    def returnDepositsWithdrawals(self, start_ts, end_ts):
        return self.api_query('returnDepositsWithdrawals', {'start': start_ts, 'end': end_ts})

    def returnActiveLoans(self):
        return self.api_query('returnActiveLoans')

    def returnOpenLoanOffers(self):
        return self.api_query('returnOpenLoanOffers')

    def createLoanOffer(self, currency, amount, duration, autoRenew, lendingRate):
        resp = self.api_query(
            'createLoanOffer', {
                'currency': currency,
                'amount': amount,
                'duration': duration,
                'autoRenew': autoRenew,
                'lendingRate': lendingRate
            }
        )
        if 'success' not in resp or resp['success'] == 0:
            raise PoloniexError(
                "Poloniex Error. Failed to create a Loan Order.\n{}".format(
                    resp['error'])
            )
        return resp['orderID']

    def cancelLoanOffer(self, orderNumber):
        resp = self.api_query(
            'cancelLoanOffer', {'orderNumber': orderNumber}
        )
        if 'success' not in resp:
            raise PoloniexError(
                "Poloniex Error. Failed to cancel Loan Order '{}'\n{}".format(
                    orderNumber, resp['error'])
            )

    # Places a buy order in a given market.
    # Required POST parameters are "currencyPair", "rate", and "amount".
    # If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is buying at
    # amount        Amount of coins to buy
    # Outputs:
    # orderNumber   The order number
    def buy(self, currencyPair, rate, amount):
        return self.api_query(
            'buy', {
                "currencyPair": currencyPair,
                "rate": rate,
                "amount": amount
            })

    def buy_fill_or_kill(self, currencyPair, rate, amount):
        return self.api_query(
            'buy', {
                "currencyPair": currencyPair,
                "rate": rate,
                "amount": amount,
                "fillOrKill": 1
            })

    # Places a sell order in a given market.
    # Required POST parameters are "currencyPair", "rate", and "amount".
    # If successful, the method will return the order number.
    # Inputs:
    # currencyPair  The curreny pair
    # rate          price the order is selling at
    # amount        Amount of coins to sell
    # Outputs:
    # orderNumber   The order number
    def sell(self, currencyPair, rate, amount):
        return self.api_query(
            'sell', {
                "currencyPair": currencyPair,
                "rate": rate,
                "amount": amount}
        )

    def sell_fill_or_kill(self, currencyPair, rate, amount):
        return self.api_query(
            'sell', {
                "currencyPair": currencyPair,
                "rate": rate,
                "amount": amount,
                "fillOrKill": 1
            })

    # Cancels an order you have placed in a given market.
    # Required POST parameters are "currencyPair" and "orderNumber".
    # Inputs:
    # currencyPair  The curreny pair
    # orderNumber   The order number to cancel
    # Outputs:
    # succes        1 or 0
    def cancel(self, currencyPair, orderNumber):
        return self.api_query(
            'cancelOrder', {
                "currencyPair": currencyPair,
                "orderNumber": orderNumber
            })

    # Immediately places a withdrawal for a given currency, with no email
    # confirmation. In order to use this method, the withdrawal privilege must
    # be enabled for your API key.
    # Required POST parameters are "currency", "amount", and "address".
    # Sample output: {"response":"Withdrew 2398 NXT."}
    # Inputs:
    # currency      The currency to withdraw
    # amount        The amount of this coin to withdraw
    # address       The withdrawal address
    # Outputs:
    # response      Text containing message about the withdrawal
    def withdraw(self, currency, amount, address):
        return self.api_query(
            'withdraw', {
                "currency": currency,
                "amount": amount,
                "address": address
            })

    def market_watcher(self):
        self.ticker = self.returnTicker()
        with self.lock:
            self.usdprice['BTC'] = FVal(self.ticker['USDT_BTC']['last'])
            self.usdprice['ETH'] = FVal(self.ticker['USDT_ETH']['last'])
            self.usdprice['DASH'] = FVal(self.ticker['USDT_DASH']['last'])
            self.usdprice['XMR'] = FVal(self.ticker['USDT_XMR']['last'])
            self.usdprice['LTC'] = FVal(self.ticker['USDT_LTC']['last'])
            self.usdprice['MAID'] = FVal(self.ticker['BTC_MAID']['last']) * self.usdprice['BTC']
            self.usdprice['FCT'] = FVal(self.ticker['BTC_FCT']['last']) * self.usdprice['BTC']

    def main_logic(self):
        if not self.first_connection_made:
            return

        try:
            self.market_watcher()

        except PoloniexError as e:
            logger.error("Poloniex error at main loop: {}".format(str(e)))
        except Exception as e:
            logger.error(
                "\nException at main loop: {}\n{}\n".format(
                    str(e), traceback.format_exc())
            )

    # ---- General exchanges interface ----
    def order_book(self, currencyPair=None):
        currencyPair = 'all' if currencyPair is None else currencyPair
        return self.api_query(
            "returnOrderBook",
            {'currencyPair': currencyPair}
        )

    @cache_response_timewise()
    def query_balances(self):
        resp = self.api_query('returnCompleteBalances', {"account": "all"})
        balances = dict()
        for currency, v in resp.items():
            available = FVal(v['available'])
            on_orders = FVal(v['onOrders'])
            if (available != FVal(0) or on_orders != FVal(0)):
                entry = {}
                entry['amount'] = available + on_orders
                usd_price = self.inquirer.find_usd_price(
                    asset=currency,
                    asset_btc_price=None
                )
                usd_value = entry['amount'] * usd_price
                entry['usd_value'] = usd_value
                balances[currency] = entry
        return balances

    def query_trade_history(self, start_ts, end_ts, end_at_least_ts):
        with self.lock:
            cache = self.check_trades_cache(start_ts, end_at_least_ts)
        if cache is not None:
            return cache

        result = self.returnTradeHistory(
            currencyPair='all',
            start=start_ts,
            end=end_ts
        )

        with self.lock:
            self.update_trades_cache(result, start_ts, end_ts)
        return result

    def parseLoanCSV(self):
        # the default filename, and should be (if at all) inside the data directory
        path = os.path.join(self.data_dir, "lendingHistory.csv")
        lending_history = list()
        with open(path, 'rb') as csvfile:
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

    def query_loan_history(self, start_ts, end_ts, end_at_least_ts=None, from_csv=False):
        """
        WARNING: Querying from returnLendingHistory endpoing instead of reading from
        the CSV file can potentially  return unexpected/wrong results.

        That is because the `returnLendingHistory` endpoint has a hidden limit
        of 12660 results. In our code we use the limit of 12000 but poloniex may change
        the endpoint to have a lower limit at which case this code will break.

        To be safe compare results of both CSV and endpoint to make sure they agree!
        """
        try:
            if from_csv:
                return self.parseLoanCSV()
        except:
            pass

        with self.lock:
            cache = self.check_trades_cache(start_ts, end_at_least_ts, special_name='loan_history')
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
        # if poloniex can guarantee me that the order is going to be ascending/descending
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

    def query_deposits_withdrawals(self, start_ts, end_ts, end_at_least_ts):
        with self.lock:
            cache = self.check_trades_cache(
                start_ts,
                end_at_least_ts,
                special_name='deposits_withdrawals'
            )
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
                exchange='poloniex',
                category='withdrawal',
                timestamp=withdrawal['timestamp'],
                asset=withdrawal['currency'],
                amount=FVal(withdrawal['amount']),
                fee=FVal(withdrawal['fee'])
            ))

        for deposit in result['deposits']:
            movements.append(AssetMovement(
                exchange='poloniex',
                category='deposit',
                timestamp=deposit['timestamp'],
                asset=deposit['currency'],
                amount=FVal(deposit['amount']),
                fee=0
            ))

        return movements
