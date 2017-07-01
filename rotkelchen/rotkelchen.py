#!/usr/bin/env python
from __future__ import division

import os
import json
import threading
import urllib2
import plot

from utils import (
    Logger,
    combine_stat_dicts,
    pretty_json_dumps,
    from_wei,
    dict_get_sumof,
    merge_dicts,
    rlk_jsonloads,
)

from poloniex import Poloniex
from kraken import Kraken
from bittrex import Bittrex
from data import DataHandler
from inquirer import Inquirer
from utils import query_fiat_pair
from fval import FVal


class Rotkelchen(object):
    def __init__(self, args):
        self.lock = threading.Lock()
        self.lock.acquire()

        self.sleep_secs = args.sleep_secs
        data_dir = args.data_dir

        # read the secret data (api keys e.t.c)
        self.secret_name = os.path.join(data_dir, 'secret.json')
        self.secret_data = {}
        if os.path.isfile(self.secret_name):
            with open(self.secret_name, 'r') as f:
                self.secret_data = rlk_jsonloads(f.read())

        # turn all secret key values from unicode to string
        for k, v in self.secret_data.iteritems():
            self.secret_data[k] = str(self.secret_data[k])

        # if a file is given open it for output and initialize the logger
        outfile = None
        self.args = args
        if args.output:
            outfile = open(args.output, 'w+')
        self.logger = Logger(outfile, args.notify)

        self.cache_data_filename = os.path.join(data_dir, 'cache_data.json')

        self.poloniex = None
        self.kraken = None
        self.bittrex = None

        # initialize exchanges for which we have keys
        if 'polo_api_key' in self.secret_data:
            self.poloniex = Poloniex(
                self.secret_data['polo_api_key'],
                self.secret_data['polo_secret'],
                args,
                self.logger,
                self.cache_data_filename,
                data_dir
            )
        if 'kraken_api_key' in self.secret_data:
            self.kraken = Kraken(
                self.secret_data['kraken_api_key'],
                self.secret_data['kraken_secret'],
                args,
                self.logger,
                data_dir
            )
        self.inquirer = Inquirer(kraken=self.kraken if hasattr(self, 'kraken') else None)
        if 'bittrex_api_key' in self.secret_data:
            self.bittrex = Bittrex(
                self.secret_data['bittrex_api_key'],
                self.secret_data['bittrex_secret'],
                self.inquirer,
                data_dir
            )

        self.data = DataHandler(
            self.logger,
            self.poloniex,
            self.kraken,
            self.bittrex,
            data_dir
        )
        self.main_currency = self.data.accountant.profit_currency

        self.lock.release()
        self.condition_lock = threading.Condition()
        self.shutdown_event = threading.Event()
        self.worker_thread = threading.Thread(target=self.main_loop, args=())
        self.worker_thread.start()

    def main_loop(self):
        while True and not self.shutdown_event.is_set():
            with self.lock:
                if self.poloniex is not None:
                    self.poloniex.main_logic()
                if self.kraken is not None:
                    self.kraken.main_logic()

            with self.condition_lock:
                if self.condition_lock.wait(self.sleep_secs):
                    break

    def plot(self):
        plot.show(self.data.stats)
        return pretty_json_dumps(self.data.stats)

    def process_history(self, start_ts, end_ts):
        return self.data.process_history(start_ts, end_ts)

    def query_blockchain_balances(self):
        # Find balance of eth Accounts
        eth_resp = urllib2.urlopen(
            urllib2.Request(
                'https://api.etherscan.io/api?module=account&action=balancemulti&address=%s' %
                ','.join(self.data.personal['eth_accounts'])
            )
        )
        eth_resp = rlk_jsonloads(eth_resp.read())
        if eth_resp['status'] != '1':
            raise ValueError('Failed to query etherscan for accounts balance')
        eth_resp = eth_resp['result']
        eth_sum = 0
        for account_entry in eth_resp:
            eth_sum += from_wei(FVal(account_entry['balance']))

        eth_usd_price = self.inquirer.find_usd_price('ETH')
        eth_accounts_usd_amount = eth_sum * eth_usd_price
        blockchain_balances = {
            'ETH': {
                'amount': eth_sum, 'usd_value': eth_accounts_usd_amount}
        }

        # Get the prices for all stuff from coinmarketcap
        coinmarketcap_resp = urllib2.urlopen(
            urllib2.Request('https://api.coinmarketcap.com/v1/ticker/')
        )
        coinmarketcap_resp = rlk_jsonloads(coinmarketcap_resp.read())
        # For now I only have one address holding a token. In the future if I
        # spread them in different addresses gotta search for token balance in
        # each address
        tokens = self.data.personal['tokens']
        for result in coinmarketcap_resp:
            if result['symbol'] in tokens:
                tokens[result['symbol']]['usd_price'] = FVal(result['price_usd'])

        for token_name, data in tokens.iteritems():
            resp = urllib2.urlopen(
                urllib2.Request(
                    'https://api.etherscan.io/api?module=account&action='
                    'tokenbalance&contractaddress={}&address={}'.format(
                        data['token_address'],
                        data['holding_address']
                    )))
            resp = rlk_jsonloads(resp.read())
            if resp['status'] != '1':
                raise ValueError('Failed to query etherscan for token balance')
            amount = FVal(resp['result']) / data['digits_divisor']
            token_usd_price = data.get('usd_price', 0)
            if token_usd_price == 0:
                print("-------> Etherscan has no USD price for token: {}".format(token_name))
            blockchain_balances[token_name] = {
                'amount': amount, 'usd_value': amount * token_usd_price
            }

        return blockchain_balances

    def query_bank_balances(self):
        eur_usd_price = query_fiat_pair('EUR', 'USD')
        return {
            'EUR': {
                'amount': FVal(self.data.personal['euros']),
                'usd_value': self.data.personal['euros'] * eur_usd_price
            }
        }

    def query_balances(self, save_data=False):
        polo = self.poloniex.query_balances()
        kraken = self.kraken.query_balances()
        bittrex = self.bittrex.query_balances()
        blockchain_balances = self.query_blockchain_balances()
        bank_balances = self.query_bank_balances()

        combined = combine_stat_dicts(polo, kraken, bittrex, blockchain_balances, bank_balances)

        polo_net_usd = dict_get_sumof(polo, 'usd_value')
        kraken_net_usd = dict_get_sumof(kraken, 'usd_value')
        bittrex_net_usd = dict_get_sumof(bittrex, 'usd_value')
        crypto_net_usd = dict_get_sumof(blockchain_balances, 'usd_value')

        # calculate net usd value
        net_usd = FVal(0)
        for k, v in combined.iteritems():
            net_usd += FVal(v['usd_value'])

        stats = {
            'location': {
                'percentage_of_net_usd_in_poloniex': (polo_net_usd / net_usd).to_percentage(),
                'percentage_of_net_usd_in_kraken': (kraken_net_usd / net_usd).to_percentage(),
                'percentage_of_net_usd_in_bittrex': (bittrex_net_usd / net_usd).to_percentage(),
                'percentage_of_net_usd_in_normal_crypto_account': (crypto_net_usd / net_usd).to_percentage(),
                'percentage_of_net_usd_in_banksncash': (bank_balances['EUR']['usd_value'] / net_usd).to_percentage(),
            },
            'net_usd': net_usd
        }

        currencies = {}
        for k, v in combined.iteritems():
            currencies['percentage_of_net_usd_in_{}'.format(k.lower())] = (v['usd_value'] / net_usd).to_percentage(),
        stats['currencies'] = currencies

        result_dict = merge_dicts(combined, stats)

        if save_data:
            self.data.append_to_stats(result_dict)

        # After adding it to the saved file we can overlay additional data that
        # is not required to be saved in the history file
        try:
            details = self.data.accountant.details
            for asset, (tax_free_amount, average_buy_value) in details.iteritems():
                if asset not in result_dict:
                    continue

                result_dict[asset]['tax_free_amount'] = tax_free_amount
                result_dict[asset]['average_buy_value'] = average_buy_value

                current_price = result_dict[asset]['usd_value'] / result_dict[asset]['amount']
                if average_buy_value != FVal(0):
                    result_dict[asset]['percent_change'] = (
                        ((current_price - average_buy_value) / average_buy_value) * 100
                    )
                else:
                    result_dict[asset]['percent_change'] = 'INF'

        except AttributeError:
            pass

        return result_dict

    def set_main_currency(self, currency):
        self.data.set_main_currency(currency)
        if currency != 'USD':
            self.usd_to_main_currency_rate = query_fiat_pair('USD', currency)

    def usd_to_main_currency(self, amount):
        if self.main_currency != 'USD' and not hasattr(self, 'usd_to_main_currency_rate'):
            self.usd_to_main_currency_rate = query_fiat_pair('USD', self.main_currency)

        return self.usd_to_main_currency_rate * amount

    def get_exchanges(self):
        exchanges = list()
        if 'polo_api_key' in self.secret_data:
            exchanges.append('poloniex')
        if 'kraken_api_key' in self.secret_data:
            exchanges.append('kraken')
        if 'bittrex_api_key' in self.secret_data:
            exchanges.append('bittrex')
        return exchanges

    def shutdown(self):
        print("Shutting Down...")
        self.shutdown_event.set()
        with self.condition_lock:
            self.condition_lock.notify_all()
        self.worker_thread.join()
        self.logger.destroy()

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


# For testing purposes only
if __name__ == '__main__':
    from args import app_args
    args = app_args()
    r = Rotkelchen(args)
