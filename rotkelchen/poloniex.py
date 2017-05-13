#!/usr/bin/env python

import urllib
import urllib2
import json
import time
import hmac
import hashlib
import datetime
import os
import traceback

from utils import (
    sfjson_loads,
    createTimeStamp,
    dateToTs,
    pretty_json_dumps,
    floatToStr,
    percToStr
)
from exchange import Exchange
from lender import Lender
from errors import PoloniexError

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

    def __init__(self, api_key, secret, args, save_file, logger):
        super(Poloniex, self).__init__('poloniex', api_key, secret)

        self.args = args
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

        self.save_file = save_file
        data = None
        if os.path.isfile(self.save_file):
            with open(self.save_file, 'r') as f:
                data = sfjson_loads(f.read())
                if 'poloniex' in data:
                    data = data['poloniex']

        self.log = logger
        self.usdprice = {}

        fees_resp = self.returnFeeInfo()
        self.maker_fee = float(fees_resp['makerFee'])
        self.taker_fee = float(fees_resp['takerFee'])

    def post_process(self, before):
        after = before

        # Add timestamps if there isnt one but is a datetime
        if('return' in after):
            if(isinstance(after['return'], list)):
                for x in xrange(0, len(after['return'])):
                    if(isinstance(after['return'][x], dict)):
                        if('datetime' in after['return'][x]
                           and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(
                                createTimeStamp(after['return'][x]['datetime'])
                            )

        return after

    def api_query(self, command, req={}):
        try:
            if(command == "returnTicker" or command == "return24Volume"):
                ret = urllib2.urlopen(
                    urllib2.Request(
                        'https://poloniex.com/public?command=' + command
                    ))
                return json.loads(ret.read())
            elif(command == "returnOrderBook"):
                ret = urllib2.urlopen(
                    urllib2.Request(
                        'https://poloniex.com/public?command=' +
                        command + '&currencyPair=' + str(req['currencyPair']))
                )
                return json.loads(ret.read())
            elif(command == "returnMarketTradeHistory"):
                ret = urllib2.urlopen(
                    urllib2.Request(
                        'https://poloniex.com/public?command='
                        + "returnTradeHistory" +
                        '&currencyPair=' +
                        str(req['currencyPair']))
                )
                return json.loads(ret.read())
            elif(command == "returnLoanOrders"):
                ret = urllib2.urlopen(
                    urllib2.Request(
                        'https://poloniex.com/public?command='
                        + "returnLoanOrders" +
                        '&currency=' +
                        str(req['currency']))
                )
                return json.loads(ret.read())
            else:
                req['command'] = command
                req['nonce'] = int(time.time()*1000)
                post_data = urllib.urlencode(req)

                sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
                headers = {
                    'Sign': sign,
                    'Key': self.api_key
                }

                ret = urllib2.urlopen(urllib2.Request(
                    'https://poloniex.com/tradingApi',
                    post_data,
                    headers)
                )
                jsonRet = json.loads(ret.read())
                return self.post_process(jsonRet)
        except Exception as e:
            raise PoloniexError(
                'Error at Poloniex api_query(): {}\n{}'.format(
                    e, traceback.format_exc())
            )

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
        self.usdprice['BTC'] = float(self.ticker['USDT_BTC']['last'])
        self.usdprice['ETH'] = float(self.ticker['USDT_ETH']['last'])
        self.usdprice['DASH'] = float(self.ticker['USDT_DASH']['last'])
        self.usdprice['XMR'] = float(self.ticker['USDT_XMR']['last'])
        self.usdprice['LTC'] = float(self.ticker['USDT_LTC']['last'])
        self.usdprice['MAID'] = float(self.ticker['BTC_MAID']['last']) * self.usdprice['BTC']
        self.usdprice['FCT'] = float(self.ticker['BTC_FCT']['last']) * self.usdprice['BTC']

    def price_notifier(self):
        for currency, watched_settings in self.watched_currencies.iteritems():
            if currency not in self.ticker:
                self.log.output(
                    "ERROR: Could not find currency pair '{}'".format(currency)
                )
                continue
            price = float(self.ticker[currency]['last'])

            threshold = float(watched_settings.threshold)
            high = float(watched_settings.high)
            low = float(watched_settings.low)
            last_price = float(watched_settings.last)
            percent_24hr = float(self.ticker[currency]['percentChange'])
            if threshold and high - price <= threshold:
                self.log.notify(
                    "{} Approaching High".format(currency),
                    "{} last trade was at {}, which is close to the configured"
                    " high price {} to watch "
                    "for".format(currency, floatToStr(price), floatToStr(high))
                )
            elif price >= high:
                self.log.notify(
                    "{} Is At High".format(currency),
                    "{} last trade was at {}, which is above the configured"
                    " high price {} to watch "
                    "for".format(currency, floatToStr(price), floatToStr(high))
                )
            elif threshold and price - low <= threshold:
                self.log.notify(
                    "{} Approaching Low".format(currency),
                    "{} last trade was at {}, which is close to the configured"
                    " low price {} to watch "
                    "for".format(currency, floatToStr(price), floatToStr(low))
                )
            elif price <= low:
                self.log.notify(
                    "{} Is At Low".format(currency),
                    "{} last trade was at {}, which is below the configured"
                    " low price {} to watch "
                    "for".format(currency, floatToStr(price), floatToStr(low))
                )

            # find out how much price changed
            downwards = False
            if last_price == 0:
                perc = 0.0
            elif price >= last_price:
                perc = price / last_price - 1.0
            else:
                perc = 1.0 - price / last_price
                downwards = True

            # notify about actual price change above limit
            limit = 0.01
            if perc >= limit:
                self.log.notify(
                    "{} > 1% change".format(currency),
                    "{} changed by {}% {} since the last "
                    "time I checked".format(
                        currency,
                        percToStr(perc),
                        'downwards' if downwards else 'upwards'
                    )
                )

            diff = abs(percent_24hr - watched_settings.last_percentage)
            if percent_24hr >= 0.05 and diff >= 0.01:
                self.log.notify(
                    "{} 24hr % change".format(currency),
                    "{} is has changed by {}{}% in the last 24 hours".format(
                        currency,
                        "+" if percent_24hr >= 0 else "-",
                        percToStr(abs(percent_24hr))
                    )
                )
                watched_settings.last_percentage = percent_24hr

            self.log.output(
                "{}\ncurrent_price:{}\n"
                "last_price: {}\npercentage_change:{}".format(
                    currency,
                    floatToStr(price),
                    floatToStr(last_price),
                    percToStr(perc)
                )
            )

            # set last price
            watched_settings.last = price

    def main_logic(self):
        try:
            self.market_watcher()

            if self.args.price_notify:
                self.price_notifier()

        except PoloniexError as e:
            self.log.output("Poloniex error at main loop: {}".format(str(e)))
        except Exception as e:
            self.log.output(
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

    def query_balances(self):
        resp = self.api_query('returnCompleteBalances', {"account": "all"})

        balances = {}
        for currency, v in resp.iteritems():
            available = float(v['available'])
            on_orders = float(v['onOrders'])
            btc_value = float(v['btcValue'])
            if (available != 0.0 or on_orders != 0.0):
                entry = {}
                entry['amount'] = available + on_orders
                try:
                    usd_value = entry['amount'] * self.usdprice[currency]
                except:
                    usd_value = btc_value * self.usdprice['BTC']
                entry['usd_value'] = usd_value
                balances[currency] = entry

        return balances
