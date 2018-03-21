#!/usr/bin/env python
import os
import csv
from datetime import datetime

from rotkehlchen.utils import createTimeStamp, dateToTs, isclose
from rotkehlchen.errors import PoloniexError
from rotkehlchen.fval import FVal

import logging
logger = logging.getLogger(__name__)


def rateToStr(f):
    return "{:10.6f}".format(f)


def eqRate(a, b):
    return isclose(a, b, 1e-3)


def gtRate(a, b):
    return a - b > 1e-7


def ltRate(a, b):
    return b - a > 1e-7


def deserialize(obj, d):
    # Not using pickle since not all attributes are serialized/deserialized
    for k, v in d.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
        else:
            print (
                "ERROR: Attribute '{}' not found on {} during "
                "deserialization".format(k, obj.__class__.__name__)
            )


class Lender:
    settings = [
        'currencies',
        'min_rate',
        'acc_threshold',
        'offer_threshold',
        'total_allowed'
    ]

    def __init__(self, poloniex, lending_history_file, data):
        # Set default attribute values
        self.currencies = [
            'ETH',
            'BTC',
            'DASH',
            'XMR',
            'LTC',
            'MAID',
            'FCT',
        ]
        self.min_rate = {
            'ETH': 0.0000200,
            'BTC': 0.00010,
            'DASH': 0.000070,
            'XMR': 0.000020,
            'MAID': 0.000020,
            'LTC': 0.000010,
            'FCT': 0.000010,
        }
        self.acc_threshold = {
            'ETH': 2.0,
            'BTC': 0.0,
            'DASH': 0.0,
            'XMR': 0.0,
            'MAID': 0.0,
            'LTC': 0.0,
            'FCT': 0.0,
        }
        self.offer_threshold = {
            'ETH': 1000,
            'BTC': 15.0,
            'DASH': 50.0,
            'XMR': 1000.0,
            'MAID': 100.0,
            'LTC': 50.0,
            'FCT': 50.0,
        }
        self.min_offer_threshold = {
            'ETH': 200,
            'BTC': 1.0,
            'DASH': 10.0,
            'XMR': 10.0,
            'MAID': 50.0,
            'LTC': 10.0,
            'FCT': 10.0,
        }
        self.total_allowed = {
            'ETH': 10100,
            'BTC': 50.0,
            'DASH': 1500.0,
            'XMR': 100.0,
            'MAID': 1000000.0,
            'LTC': 1500.0,
            'FCT': 1500.0,
        }
        self.percentage_to_maximize_days = 0.005

        if data:
            deserialize(self, data)
        self.p = poloniex

        # initialize some dictionaries
        self.lending_rate = {}
        self.amount_in_loans = {}
        self.amount_in_account = {}
        self.amount_in_offers = {}
        self.active_profit = {}
        self.historical_earnings = {}
        for currency in self.currencies:
            self.historical_earnings[currency] = 0.0

        self.lending_history_file = lending_history_file
        self.lending_history_modified = 0
        self.lending_history = []

    def get_settings(self):
        d = {}
        for s in self.settings:
            d[s] = getattr(self, s)
        return d

    def set(self, *args):
        setting = args[0]
        if setting not in self.settings:
            raise Exception(
                "Requested to set unknown attribute '{}' in Lender".format(
                    setting)
            )

        if isinstance(getattr(self, setting), dict):
            pos = getattr(self, setting)
            pr_pos = pos
            v_type = float
            for idx, a in enumerate(args[1:]):
                if a not in pos:
                    raise Exception(
                        "Could not find key '{}' in Lender's '{}' "
                        "setting".format(a, setting)
                    )
                pos = pos[a]
                if idx == len(args) - 3:
                    if isinstance(pr_pos, dict):
                        pr_pos[a] = v_type(args[-1])
                    else:
                        pr_pos = v_type(args[-1])
                    break
                pr_pos = pos
        else:
            setattr(self, setting, args[1])

        return "Set Lender's '{}' to '{}'".format(
            setting, getattr(self, setting)
        )

    def parseLoanCSV(self, path):
        self.lending_history = []
        with open(path, 'rb') as csvfile:
            history = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(history)  # skip header row
            for row in history:
                self.lending_history.append({
                    'currency': row[0],
                    'earned': FVal(row[6]),
                    'amount': FVal(row[2]),
                    'opened': createTimeStamp(row[7]),
                    'closed': createTimeStamp(row[8])
                })
        return self.lending_history

    def parseLoanCSV_for_analysis(self, from_timestamp, to_timestamp, currency):
        lending_history = []
        with open(self.lending_history_file, 'rb') as csvfile:
            history = csv.reader(csvfile, delimiter=',', quotechar='|')
            next(history)  # skip header row
            for row in history:
                lending_history.append({
                    'currency': row[0],
                    'rate': float(row[1]),
                    'amount': float(row[2]),
                    'earned': float(row[6]),
                    'opened': createTimeStamp(row[7]),
                    'closed': createTimeStamp(row[8])
                })

        if not isinstance(from_timestamp, (int, long)):
            from_timestamp = dateToTs(from_timestamp)
        if not isinstance(to_timestamp, (int, long)):
            to_timestamp = dateToTs(to_timestamp)

        # find average lending rate over all loans
        average_rate = 0.0
        average_duration = 0
        count = 0
        minTs = 9999999999999999999
        maxTs = 0
        secscount = 0
        daycount = 0
        daily_earned = 0
        average_daily_earned = 0
        daily_lent = 0
        average_daily_lent = 0
        previousTs = lending_history[0]['opened']
        for loan in lending_history:
            if loan['currency'] != currency:
                continue

            if loan['opened'] < from_timestamp:
                continue
            if loan['closed'] > to_timestamp:
                continue  # TODO just break since csv is ordered

            if loan['opened'] > maxTs:
                maxTs = loan['opened']
            if loan['opened'] < minTs:
                minTs = loan['opened']

            diff = previousTs - loan['opened']
            duration = loan['closed'] - loan['opened']
            if secscount + diff > 86400:
                daycount += 1
                secscount = 0
                average_daily_earned += daily_earned
                daily_earned = 0
                average_daily_lent += daily_lent
                daily_lent = 0
            else:
                secscount += diff
                daily_earned += loan['earned']
                daily_lent += loan['amount'] * duration / 86400

            previousTs = loan['opened']
            average_rate += loan['rate']
            average_duration += duration
            count += 1

        average_rate /= count
        average_duration /= count
        average_daily_earned /= daycount
        average_daily_lent /= daycount

        s = """LENDING ANALYSIS for {}
-----------------------------------
From {} to {}
Average Lending rate: {}
Average duration: {} hours
Average {} lent per day: {}
Average {} earned per day: {}
""".format(
            currency,
            unicode(datetime.utcfromtimestamp(minTs)),
            unicode(datetime.utcfromtimestamp(maxTs)),
            rateToStr(average_rate),
            average_duration / 3600,
            currency,
            average_daily_lent,
            currency,
            average_daily_earned,
        )
        return s

    def lending_total_earned(self, start=None, end=None):
        for currency in self.historical_earnings:
            self.historical_earnings[currency] = 0.0

        if self.lending_history != []:
            if start:
                start = dateToTs(start)
            if end:
                end = dateToTs(end)
            for loan in self.lending_history:
                if start and loan['opened'] < start:
                    continue
                if end and loan['closed'] > end:
                    continue
                self.historical_earnings[loan['currency']] += loan['earned']

    def check_lending_history(self):
        if not self.lending_history_file:
            return
        if not os.path.isfile(self.lending_history_file):
            return

        modified = os.path.getmtime(self.lending_history_file)
        if modified <= self.lending_history_modified:
            return

        if logger.isEnabledFor(logging.INFO):
            logger.info("Lending history file has been modified. Reloading!")
        self.lending_history_modified = modified
        self.lending_history = self.parseLoanCSV(self.lending_history_file)

    def query_loans(self, start=None, end=None):
        s = "LENDING STATUS\n-----------------------------------"
        total_usd = 0.0
        for currency in self.currencies:
            s += "\n==={}===\n".format(currency)
            s += "Best lending rate found for {} is {}\n".format(
                currency,
                rateToStr(self.lending_rate[currency])
            )
            s += "{} in lending account: {}\n".format(
                currency,
                self.amount_in_account[currency]
            )
            s += "{} in active loans: {}\n".format(
                currency,
                self.amount_in_loans[currency]
            )
            s += "{} in open loan offers: {}\n".format(
                currency,
                self.amount_in_offers[currency]
            )
            s += "Historical lending earnings so far: {}\n".format(
                self.historical_earnings[currency]
            )
            s += "Earnings from active loans: {}\n".format(
                self.active_profit[currency]
            )
            total = (
                float(self.historical_earnings[currency]) +
                float(self.active_profit[currency])
            )
            s += "Sum of active and historical loan profits: {}".format(total)
            total_usd += total * self.p.usdprice[currency]
        s += (
            "\n-------------------------\nTotal USD profit from loans: "
            "{}\n".format(total_usd)
        )
        return s

    def loans_per_currency(self, currency, alrsp, oorsp):
        sum_amount = 0.0
        sum_active_profit = 0.0

        for loan in alrsp['provided']:
            if loan['currency'] == currency:
                sum_amount += float(loan['amount'])
                sum_active_profit += float(loan['fees'])

        self.amount_in_loans[currency] = sum_amount
        self.active_profit[currency] = sum_active_profit

        sum_open_offers = 0.0
        offer_rate = 0.0
        if oorsp and currency in oorsp:
            for loan in oorsp[currency]:
                sum_open_offers += float(loan['amount'])
                offer_rate = float(loan['rate'])
        self.amount_in_offers[currency] = sum_open_offers

        abrsp = self.p.returnAvailableAccountBalances()
        self.amount_in_account[currency] = 0.0
        if 'lending' in abrsp and currency in abrsp['lending']:
            self.amount_in_account[currency] = float(
                abrsp['lending'][currency]
            )

        # Determine the offer threshold
        offer_threshold = self.offer_threshold[currency]
        sum_of_lending_holdings = self.amount_in_account[currency] + self.amount_in_offers[currency]
        if sum_of_lending_holdings < offer_threshold:
            offer_threshold = sum_of_lending_holdings + (offer_threshold - sum_of_lending_holdings) / offer_threshold * sum_of_lending_holdings
            if offer_threshold < self.min_offer_threshold[currency]:
                offer_threshold = self.min_offer_threshold[currency]

        # Check current orders and find the best rate
        orders = self.p.returnLoanOrders(currency)
        best_rate = 0.0
        pr_best_rate = 0.0
        rate_step = 0.0
        sum_of_other_offers = 0.0
        if orders['offers']:
            for offer in orders['offers']:
                this_rate = float(offer['rate'])
                this_amount = float(offer['amount'])

                # Do not count our own offers when deciding the best rate
                if eqRate(this_rate, offer_rate):
                    if this_amount >= sum_open_offers:
                        this_amount -= sum_open_offers
                        sum_open_offers = 0
                    else:
                        sum_open_offers -= this_amount
                        this_amount = 0
                sum_of_other_offers += this_amount

                if sum_of_other_offers < offer_threshold:
                    best_rate = this_rate
                    if not eqRate(best_rate, pr_best_rate):
                        rate_step = best_rate - pr_best_rate
                        pr_best_rate = best_rate

                else:
                    break

        info_enabled = logger.isEnabledFor(logging.INFO)
        if info_enabled:
            logger.info("Best {} lending rate found: {}".format(
                currency, rateToStr(best_rate))
            )
            logger.info("Lending rate step for {} found: {}".format(
                currency,
                rateToStr(rate_step)
            ))
        # Also remember the best rate, to show it at query_loans
        self.lending_rate[currency] = best_rate

        if self.amount_in_loans[currency] + self.amount_in_account[currency] > self.total_allowed[currency]:
            if info_enabled:
                logger.info(
                    "Already have {} {} in loans + account. Total allowed for lending is: "
                    "{} {}. Doing nothing...".format(
                        self.amount_in_loans[currency],
                        currency,
                        self.total_allowed[currency],
                        currency)
                )
            return

        if gtRate(self.min_rate[currency], best_rate):
            if info_enabled:
                logger.info(
                    "Minimum rate {} is bigger than the best rate. Doing "
                    "nothing...".format(rateToStr(self.min_rate[currency]))
                )
            return

        # If that's a better rate than our open offers, cancel them
        if offer_rate != 0.0 and gtRate(best_rate, offer_rate):
            if info_enabled:
                logger.info(
                    "Found best rate: {} is better than our offer of {}".format(
                        best_rate, offer_rate)
                )
            for loan in oorsp[currency]:
                self.amount_in_account[currency] += float(loan['amount'])
                self.p.cancelLoanOffer(int(loan['id']))
                if info_enabled:
                    logger.info("Canceling {} loan with ID:{}".format(
                        currency, int(loan['id']))
                    )
            self.amount_in_offers[currency] = 0.0

        # If the best rate is "much less" than our existing offers it means
        # the market for lending is going down. We have to adjust.
        if offer_rate != 0.0 and offer_rate - best_rate >= rate_step * 12:
            if info_enabled:
                logger.info(
                    "Found best rate: {} is much smaller than our offer of {}".format(
                        best_rate, offer_rate)
                )
            for loan in oorsp[currency]:
                self.amount_in_account[currency] += float(loan['amount'])
                self.p.cancelLoanOffer(int(loan['id']))
                if info_enabled:
                    logger.info("Canceling {} loan with ID:{}".format(
                        currency, int(loan['id']))
                    )
            self.amount_in_offers[currency] = 0.0

        # If there are open offers but we also have some amount in the account,
        # cancel them so that they will be remade
        if (
                self.amount_in_offers[currency] != 0.0 and
                self.amount_in_account[currency] > 0.5
        ):
            if info_enabled:
                logger.info(
                    "Canceling {} loan offers to remake them and include the {} "
                    "{} inside the account".format(
                        currency,
                        self.amount_in_account[currency],
                        currency)
                )
            for loan in oorsp[currency]:
                self.amount_in_account[currency] += float(loan['amount'])
                self.p.cancelLoanOffer(int(loan['id']))
                if info_enabled:
                    logger.info("Canceling {} loan with ID:{}".format(
                        currency, int(loan['id']))
                    )
                self.amount_in_offers[currency] = 0.0

        # If the amount in the account is above threshold create a new offer
        if (
                self.amount_in_account[currency] >= self.acc_threshold[currency] and
                self.amount_in_account[currency] > 0
        ):
            # If we are at a rate of more than 0.5% then maximize the number
            # of days for the loan
            number_of_days = 60 if best_rate >= self.percentage_to_maximize_days else 2
            try:
                oid = self.p.createLoanOffer(
                    currency,
                    self.amount_in_account[currency],
                    number_of_days,
                    0,
                    best_rate
                )
                if info_enabled:
                    logger.info(
                        "Created Loan Offer ({}) for {} {} at rate: {}".format(
                            oid,
                            self.amount_in_account[currency],
                            currency,
                            rateToStr(best_rate))
                    )
            except PoloniexError:
                pass

    def main_logic(self):
        self.check_lending_history()
        self.lending_total_earned()
        alrsp = self.p.returnActiveLoans()
        oorsp = self.p.returnOpenLoanOffers()
        for currency in self.currencies:
            self.loans_per_currency(currency, alrsp, oorsp)
