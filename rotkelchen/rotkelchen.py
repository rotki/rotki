#!/usr/bin/env python
from __future__ import division

import os
import json
import time
import sys
import threading
import urllib2
import plot

from utils import (
    Logger,
    combine_stat_dicts,
    pretty_json_dumps,
    from_wei,
    dict_get_sumof,
    floatToPerc,
    merge_dicts,
)

from poloniex import Poloniex
from kraken import Kraken
from bittrex import Bittrex
from data import DataHandler


class Rotkelchen(object):
    def __init__(self, args):
        self.sleep_secs = args.sleep_secs
        data_dir = args.data_dir
        self.save_file = os.path.join(data_dir, 'save.json')

        # read the secret data (api keys e.t.c)
        self.secret_name = os.path.join(data_dir, 'secret.json')
        self.secret_data = {}
        if os.path.isfile(self.secret_name):
            with open(self.secret_name, 'r') as f:
                self.secret_data = json.loads(f.read())
        else:
            print("Could not find secret.json. Unable to load API keys")
            sys.exit(1)

        # turn all secret key values from unicode to string
        for k, v in self.secret_data.iteritems():
            self.secret_data[k] = str(self.secret_data[k])

        # if a file is given open it for output and initialize the logger
        outfile = None
        self.args = args
        if args.output:
            outfile = open(args.output, 'w+')
        self.logger = Logger(outfile, args.notify)

        # initialize exchanges for which we have keys
        if 'polo_api_key' in self.secret_data:
            self.poloniex = Poloniex(
                self.secret_data['polo_api_key'],
                self.secret_data['polo_secret'],
                args,
                self.save_file,
                self.logger,
            )
        if 'kraken_api_key' in self.secret_data:
            self.kraken = Kraken(
                self.secret_data['kraken_api_key'],
                self.secret_data['kraken_secret'],
                args,
                self.save_file,
                self.logger
            )
        if 'bittrex_api_key' in self.secret_data:
            self.bittrex = Bittrex(
                self.secret_data['bittrex_api_key'],
                self.secret_data['bittrex_secret'],
                self.kraken
            )

        self.data = DataHandler(
            self.logger,
            self.poloniex,
            self.kraken,
            self.bittrex,
            data_dir
        )

    def get_settings(self):
        return {'poloniex': self.poloniex.get_settings()}

    def query_settings(self):
        s = json.dumps(
            self.get_settings(),
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )
        return s

    def plot(self):
        plot.show(self.data.stats)
        return pretty_json_dumps(self.data.stats)

    def process_history(self, resync=False):
        return self.data.process_history(resync)

    def query_balances(self, save_data=False):
        polo = self.poloniex.query_balances()
        kraken = self.kraken.query_balances()
        bittrex = self.bittrex.query_balances()

        # Find balance of eth Accounts
        eth_resp = urllib2.urlopen(
            urllib2.Request(
                'https://api.etherscan.io/api?module=account&action=balancemulti&address=%s' %
                ','.join(self.data.personal['eth_accounts'])
            )
        )
        eth_resp = json.loads(eth_resp.read())
        if eth_resp['status'] != '1':
            raise ValueError('Failed to query etherscan for accounts balance')
        eth_resp = eth_resp['result']
        eth_sum = 0
        for account_entry in eth_resp:
            eth_sum += from_wei(float(account_entry['balance']))

        eth_accounts_usd_amount = eth_sum * self.poloniex.usdprice['ETH']
        general_crypto = {
            'ETH': {
                'amount': eth_sum, 'usd_value': eth_accounts_usd_amount}
        }

        # Get the prices for all stuff from coinmarketcap
        coinmarketcap_resp = urllib2.urlopen(
            urllib2.Request('https://api.coinmarketcap.com/v1/ticker/')
        )
        coinmarketcap_resp = json.loads(coinmarketcap_resp.read())
        # For now I only have one address holding a token. In the future if I
        # spread them in different addresses gotta search for token balance in
        # each address
        tokens = self.data.personal['tokens']
        for result in coinmarketcap_resp:
            if result['symbol'] in tokens:
                tokens[result['symbol']]['usd_price'] = float(result['price_usd'])

        for token_name, data in tokens.iteritems():
            resp = urllib2.urlopen(
                urllib2.Request(
                    'https://api.etherscan.io/api?module=account&action='
                    'tokenbalance&contractaddress={}&address={}'.format(
                        data['token_address'],
                        data['holding_address']
                    )))
            resp = json.loads(resp.read())
            if resp['status'] != '1':
                raise ValueError('Failed to query etherscan for token balance')
            amount = float(resp['result']) / data['digits_divisor']
            general_crypto[token_name] = {
                'amount': amount, 'usd_value': amount * data['usd_price']
            }

        # add in the approximate bank/cash EUR I own
        banks = {
            'EUR': {
                'amount': self.data.personal['euros'],
                'usd_value': self.data.personal['euros'] * self.kraken.usdprice['EUR']}
        }

        combined = combine_stat_dicts(polo, kraken, bittrex, general_crypto, banks)

        polo_net_usd = dict_get_sumof(polo, 'usd_value')
        kraken_net_usd = dict_get_sumof(kraken, 'usd_value')
        bittrex_net_usd = dict_get_sumof(bittrex, 'usd_value')
        crypto_net_usd = dict_get_sumof(general_crypto, 'usd_value')

        # calculate net usd value
        net_usd = 0
        for k, v in combined.iteritems():
            net_usd += float(v['usd_value'])

        stats = {
            'location': {
                'percentage_of_net_usd_in_poloniex': floatToPerc(polo_net_usd/ net_usd),
                'percentage_of_net_usd_in_kraken': floatToPerc(kraken_net_usd / net_usd),
                'percentage_of_net_usd_in_bittrex': floatToPerc(bittrex_net_usd / net_usd),
                'percentage_of_net_usd_in_normal_crypto_account': floatToPerc(crypto_net_usd / net_usd),
                'percentage_of_net_usd_in_banksncash': floatToPerc(banks['EUR']['usd_value'] / net_usd)
            },
            'net_usd': net_usd
        }

        currencies = {}
        for k, v in combined.iteritems():
            currencies['percentage_of_net_usd_in_{}'.format(k.lower())] = floatToPerc(v['usd_value'] / net_usd)
        stats['currencies'] = currencies

        result_dict = merge_dicts(combined, stats)

        if save_data:
            self.data.append_to_stats(result_dict)

        # After adding it to the saved file we can overlay additional data that
        # is not required to be saved in the history file
        try:
            details = self.data.accountant.details
            for asset, (tax_free_amount, average_buy_vale) in details.iteritems():
                if asset not in result_dict:
                    continue

                result_dict[asset]['tax_free_amount'] = tax_free_amount
                result_dict[asset]['average_buy_value'] = average_buy_vale

                current_price = result_dict[asset]['usd_value'] / result_dict[asset]['amount']
                result_dict[asset]['percent_change'] = (
                    ((current_price - average_buy_vale) / average_buy_vale) * 100
                )
        except AttributeError:
            pass

        return pretty_json_dumps(result_dict)

    def shutdown(self):
        print("Shutting Down...")
        self.daemon.shutdown()
        self.logger.destroy()

        return sys.exit(0)

    def set(self, *args):
        if len(args) < 2:
            return (
                "ERROR: set requires at least two arguments but "
                "got: {}".format(args)
            )

        if args[0] == 'poloniex':
            resp = self.poloniex.set(*args[1:])
        else:
            return "ERROR: Unrecognized first argument: {}".format(args[0])

        self.save_data()
        return resp

    def save_data(self):
        current_settings = self.get_settings()
        with open(self.save_file, "w") as f:
            f.write(json.dumps(current_settings))

    def run(self):
        def main_loop():
            while True:
                self.poloniex.main_logic()
                self.kraken.main_logic()

                if self.args.arbitrage:
                    self.arbitrage.check_all()

                time.sleep(self.sleep_secs)

        thread = threading.Thread(target=main_loop)
        thread.setDaemon(True)
        thread.start()


# For testing purposes only
if __name__ == '__main__':
    from args import app_args
    args = app_args()
    r = Rotkelchen(args)
