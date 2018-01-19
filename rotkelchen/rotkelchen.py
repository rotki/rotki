#!/usr/bin/env python
import os
import gevent
from gevent.lock import Semaphore
from urllib.request import Request, urlopen

from rotkelchen.utils import (
    combine_stat_dicts,
    dict_get_sumof,
    merge_dicts,
    rlk_jsonloads,
    rlk_jsondumps,
)
from rotkelchen.plot import show_plot
from rotkelchen.ethchain import Ethchain
from rotkelchen.poloniex import Poloniex
from rotkelchen.kraken import Kraken
from rotkelchen.bittrex import Bittrex
from rotkelchen.binance import Binance
from rotkelchen.data_handler import DataHandler
from rotkelchen.inquirer import Inquirer, FIAT_CURRENCIES
from rotkelchen.utils import query_fiat_pair, cache_response_timewise
from rotkelchen.fval import FVal

import logging
logger = logging.getLogger(__name__)


class Rotkelchen(object):
    def __init__(self, args):
        self.lock = Semaphore()
        self.lock.acquire()
        self.results_cache = {}
        self.connected_exchanges = []

        logfilename = None
        if args.logtarget == 'file':
            logfilename = args.logfile

        loglevel = logging.DEBUG
        if args.loglevel == 'debug':
            loglevel = logging.DEBUG
        elif args.loglevel == 'info':
            loglevel = logging.INFO
        elif args.loglevel == 'warn':
            loglevel = logging.WARN
        elif args.loglevel == 'error':
            loglevel = logging.ERROR
        elif args.loglevel == 'critical':
            loglevel = logging.CRITICAL
        else:
            raise ValueError('Should never get here. Illegal log value')

        logging.basicConfig(
            filename=logfilename,
            filemode='w',
            level=loglevel,
            format='%(asctime)s -- %(levelname)s:%(name)s:%(message)s',
            datefmt='%d/%m/%Y %H:%M:%S %Z',
        )

        if not args.logfromothermodules:
            logging.getLogger('zerorpc').setLevel(logging.CRITICAL)
            logging.getLogger('zerorpc.channel').setLevel(logging.CRITICAL)
            logging.getLogger('urllib3').setLevel(logging.CRITICAL)
            logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

        self.sleep_secs = args.sleep_secs
        self.data_dir = args.data_dir

        # read the secret data (api keys e.t.c)
        self.secret_name = os.path.join(self.data_dir, 'secret.json')
        self.secret_data = {}
        if os.path.isfile(self.secret_name):
            with open(self.secret_name, 'r') as f:
                self.secret_data = rlk_jsonloads(f.read())

        # turn all secret key values from unicode to string
        for k, v in self.secret_data.items():
            self.secret_data[k] = str(self.secret_data[k])

        self.args = args
        self.cache_data_filename = os.path.join(self.data_dir, 'cache_data.json')

        self.ethchain = Ethchain(args.ethrpc_port)

        self.poloniex = None
        self.kraken = None
        self.bittrex = None
        self.binance = None

        # initialize exchanges for which we have keys
        if 'kraken_api_key' in self.secret_data:
            self.kraken = Kraken(
                str.encode(self.secret_data['kraken_api_key']),
                str.encode(self.secret_data['kraken_secret']),
                self.data_dir
            )
            self.connected_exchanges.append('kraken')

        self.inquirer = Inquirer(kraken=self.kraken if hasattr(self, 'kraken') else None)

        if 'poloniex_api_key' in self.secret_data:
            self.poloniex = Poloniex(
                str.encode(self.secret_data['poloniex_api_key']),
                str.encode(self.secret_data['poloniex_secret']),
                self.cache_data_filename,
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('poloniex')

        if 'bittrex_api_key' in self.secret_data:
            self.bittrex = Bittrex(
                str.encode(self.secret_data['bittrex_api_key']),
                str.encode(self.secret_data['bittrex_secret']),
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('bittrex')

        if 'binance_api_key' in self.secret_data:
            self.binance = Binance(
                str.encode(self.secret_data['binance_api_key']),
                str.encode(self.secret_data['binance_secret']),
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('binance')

        self.data = DataHandler(
            self.poloniex,
            self.kraken,
            self.bittrex,
            self.binance,
            self.data_dir
        )
        self.main_currency = self.data.accountant.profit_currency

        self.lock.release()
        self.shutdown_event = gevent.event.Event()

    def start(self):
        return gevent.spawn(self.main_loop)

    def main_loop(self):
        while True and not self.shutdown_event.is_set():
            logger.debug('Main loop start')
            if self.poloniex is not None:
                self.poloniex.main_logic()
            if self.kraken is not None:
                self.kraken.main_logic()

            logger.debug('Main loop end')
            gevent.sleep(10)

    def plot(self):
        show_plot(self.data.stats)

    def process_history(self, start_ts, end_ts):
        return self.data.process_history(start_ts, end_ts)

    @cache_response_timewise()
    def query_blockchain_balances(self):
        logger.debug('query_blockchain_balances start')
        # Find balance of eth Accounts
        eth_sum = self.ethchain.get_multieth_balance(
            self.data.personal['eth_accounts']
        )
        logger.debug('query_blockchain_balances 2')
        eth_usd_price = self.inquirer.find_usd_price('ETH')
        eth_accounts_usd_amount = eth_sum * eth_usd_price

        logger.debug('query_blockchain_balances 3')
        btc_resp = urlopen(Request(
            'https://blockchain.info/q/addressbalance/%s' %
            '|'.join(self.data.personal['btc_accounts'])
        ))
        btc_sum = FVal(btc_resp.read()) * FVal('0.00000001')  # result is in satoshis
        btc_usd_price = self.inquirer.find_usd_price('BTC')
        btc_accounts_usd_amount = btc_sum * btc_usd_price

        blockchain_balances = {
            'ETH': {
                'amount': eth_sum, 'usd_value': eth_accounts_usd_amount
            },
            'BTC': {
                'amount': btc_sum, 'usd_value': btc_accounts_usd_amount
            },
        }

        logger.debug('query_blockchain_balances 4')
        tokens_to_check = None
        if 'eth_tokens' in self.data.personal:
            tokens_to_check = self.data.personal['eth_tokens']

        for token in self.data.eth_tokens:
            try:
                token_symbol = str(token['symbol'])
            except (UnicodeDecodeError, UnicodeEncodeError):
                # skip tokens with problems in unicode encoding decoding
                continue
            if tokens_to_check and token_symbol not in tokens_to_check:
                continue

            logger.debug('query_blockchain_balances - {}'.format(token_symbol))

            token_usd_price = self.inquirer.find_usd_price(token_symbol)
            if token_usd_price == 0:
                # skip tokens that have no price
                continue

            token_amount = self.ethchain.get_multitoken_balance(
                token_symbol,
                token['address'],
                token['decimal'],
                self.data.personal['eth_accounts'],
            )
            blockchain_balances[token_symbol] = {
                'amount': token_amount, 'usd_value': token_amount * token_usd_price
            }
        logger.debug('query_blockchain_balances end')
        return blockchain_balances

    def query_bank_balances(self):
        logger.debug('At query_bank_balances start')

        result = {}
        for currency in FIAT_CURRENCIES:
            if currency in self.data.personal:
                amount = FVal(self.data.personal[currency])
                usd_rate = query_fiat_pair(currency, 'USD')
                result[currency] = {
                    'amount': amount,
                    'usd_value': amount * usd_rate
                }

        return result


    def query_balances(self, save_data=False):
        balances = {}
        for exchange in self.connected_exchanges:
            balances[exchange] = getattr(self, exchange).query_balances()

        balances['blockchain'] = self.query_blockchain_balances()
        balances['banks'] = self.query_bank_balances()

        combined = combine_stat_dicts([v for k, v in balances.items()])
        total_usd_per_location = [(k, dict_get_sumof(v, 'usd_value')) for k, v in balances.items()]

        # calculate net usd value
        net_usd = FVal(0)
        for k, v in combined.items():
            net_usd += FVal(v['usd_value'])

        stats = {
            'net_usd_perc_location': {
            },
            'net_usd': net_usd
        }
        for entry in total_usd_per_location:
            name = entry[0]
            total = entry[1]
            stats['net_usd_perc_location'][name] = (total / net_usd).to_percentage()

        for k, v in combined.items():
            combined[k]['percentage_of_net_value'] = (v['usd_value'] / net_usd).to_percentage()

        result_dict = merge_dicts(combined, stats)

        if save_data:
            self.data.append_to_stats(result_dict)

        # After adding it to the saved file we can overlay additional data that
        # is not required to be saved in the history file
        try:
            details = self.data.accountant.details
            for asset, (tax_free_amount, average_buy_value) in details.items():
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

    def extend_values(self, additional_values_path):
        """Append to the values file from another file"""
        if not os.path.isfile(additional_values_path):
            raise ValueError('Can\'t find given value file: {}'.format(additional_values_path))

        with open(additional_values_path, 'r') as f:
                new_file_dict = rlk_jsonloads(f.read())

        self.data.extend_stats(new_file_dict)

    def set_main_currency(self, currency):
        with self.lock:
            self.data.set_main_currency(currency)
            if currency != 'USD':
                self.usd_to_main_currency_rate = query_fiat_pair('USD', currency)

    def set_settings(self, settings):
        with self.lock:
            self.data.set_settings(settings)
            main_currency = settings['main_currency']
            if main_currency != 'USD':
                self.usd_to_main_currency_rate = query_fiat_pair('USD', main_currency)

    def usd_to_main_currency(self, amount):
        if self.main_currency != 'USD' and not hasattr(self, 'usd_to_main_currency_rate'):
            self.usd_to_main_currency_rate = query_fiat_pair('USD', self.main_currency)

        return self.usd_to_main_currency_rate * amount

    def get_settings(self):
        return self.data.settings

    def setup_exchange(self, name, api_key, api_secret):
        if '{}_api_key'.format(name) in self.secret_data:
            return False, 'Exchange {} is already registered'

        if not os.path.isfile(self.secret_name):
            logger.critical('The secret file can not be found')
            return False, 'The secret file can not be found'

        if name == 'kraken':
            exchange = Kraken(
                str.encode(api_key),
                str.encode(api_secret),
                self.data_dir
            )
        elif name == 'poloniex':
            exchange = Poloniex(
                str.encode(api_key),
                str.encode(api_secret),
                self.cache_data_filename,
                self.inquirer,
                self.data_dir
            )
        elif name == 'bittrex':
            exchange = Bittrex(
                str.encode(api_key),
                str.encode(api_secret),
                self.inquirer,
                self.data_dir
            )
        elif name == 'binance':
            exchange = Binance(
                str.encode(api_key),
                str.encode(api_secret),
                self.inquirer,
                self.data_dir
            )
        else:
            return False, 'Attempted to register unsupported exchange {}'.format(name)

        result, message = exchange.validate_api_key()
        if not result:
            return False, message
        # keep the exchange object
        setattr(self, name, exchange)
        self.connected_exchanges.append(name)

        self.secret_data['{}_api_key'.format(name)] = api_key
        self.secret_data['{}_secret'.format(name)] = api_secret

        with open(self.secret_name, 'w') as f:
            f.write(rlk_jsondumps(self.secret_data))

        return True, ''

    def remove_exchange(self, name):
        if '{}_api_key'.format(name) not in self.secret_data:
            return False, 'Exchange {} is not registered'

        if not os.path.isfile(self.secret_name):
            logger.critical('The secret file can not be found')
            return False, 'The secret file can not be found'

        del self.secret_data['{}_api_key'.format(name)]
        del self.secret_data['{}_secret'.format(name)]

        self.connected_exchanges.remove(name)
        with open(self.secret_name, 'w') as f:
            f.write(rlk_jsondumps(self.secret_data))

        # TODO: and finally schedule the exchange object for deletion during

        return True, ''

    def shutdown(self):
        print("Shutting Down...")
        self.shutdown_event.set()

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
