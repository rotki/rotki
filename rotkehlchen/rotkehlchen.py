#!/usr/bin/env python
import os
import gevent
import shutil
from gevent.lock import Semaphore

from rotkehlchen.utils import (
    combine_stat_dicts,
    dict_get_sumof,
    merge_dicts,
    ts_now,
)
from rotkehlchen.errors import PermissionError, AuthenticationError
from rotkehlchen.constants import SUPPORTED_EXCHANGES
from rotkehlchen.blockchain import Blockchain
from rotkehlchen.poloniex import Poloniex
from rotkehlchen.kraken import Kraken
from rotkehlchen.bittrex import Bittrex
from rotkehlchen.binance import Binance
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium import premium_create_and_verify
from rotkehlchen.utils import query_fiat_pair
from rotkehlchen.fval import FVal
from rotkehlchen.history import TradesHistorian, PriceHistorian
from rotkehlchen.accounting import Accountant

import logging
logger = logging.getLogger(__name__)


MAIN_LOOP_SECS_DELAY = 60


class Rotkehlchen(object):
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
        self.args = args
        self.last_data_upload_ts = 0

        self.poloniex = None
        self.kraken = None
        self.bittrex = None
        self.binance = None

        self.data = DataHandler(self.data_dir)

        self.lock.release()
        self.shutdown_event = gevent.event.Event()

    def initialize_exchanges(self, secret_data):
        # initialize exchanges for which we have keys and are not already initialized
        if self.kraken is None and 'kraken' in secret_data:
            self.kraken = Kraken(
                str.encode(secret_data['kraken']['api_key']),
                str.encode(secret_data['kraken']['api_secret']),
                self.data_dir
            )
            self.connected_exchanges.append('kraken')
            self.trades_historian.set_exchange('kraken', self.kraken)

        if self.poloniex is None and 'poloniex' in secret_data:
            self.poloniex = Poloniex(
                str.encode(secret_data['poloniex']['api_key']),
                str.encode(secret_data['poloniex']['api_secret']),
                self.cache_data_filename,
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('poloniex')
            self.trades_historian.set_exchange('poloniex', self.poloniex)

        if self.bittrex is None and 'bittrex' in secret_data:
            self.bittrex = Bittrex(
                str.encode(secret_data['bittrex']['api_key']),
                str.encode(secret_data['bittrex']['api_secret']),
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('bittrex')
            self.trades_historian.set_exchange('bittrex', self.bittrex)

        if self.binance is None and 'binance' in secret_data:
            self.binance = Binance(
                str.encode(secret_data['binance']['api_key']),
                str.encode(secret_data['binance']['api_secret']),
                self.inquirer,
                self.data_dir
            )
            self.connected_exchanges.append('binance')
            self.trades_historian.set_exchange('binance', self.binance)

    def try_premium_at_start(self, api_key, api_secret, create_new, sync_approval, user_dir):
        """Check if new user provided api pair or we already got one in the DB"""

        if api_key != '':
            self.premium, valid, empty_or_error = premium_create_and_verify(api_key, api_secret)
            if not valid:
                # At this point we are at a new user trying to create an account with
                # premium API keys and we failed. But a directory was created. Remove it.
                shutil.rmtree(user_dir)
                raise AuthenticationError(
                    'Could not verify keys for the new account. '
                    '{}'.format(empty_or_error)
                )
        else:
            # If we got premium initialize it and try to sync with the server
            premium_credentials = self.data.db.get_rotkehlchen_premium()
            if premium_credentials:
                api_key = premium_credentials[0]
                api_secret = premium_credentials[1]
                self.premium, valid, empty_or_error = premium_create_and_verify(api_key, api_secret)
                if not valid:
                    logger.error(
                        'The API keys found in the Database are not valid. Perhaps '
                        'they expired?'
                    )
                del self.premium
                return
            else:
                # no premium credentials in the DB
                return

        if self.can_sync_data_from_server():
            if sync_approval == 'unknown' and not create_new:
                raise PermissionError(
                    'Rotkehlchen Server has newer version of your DB data. '
                    'Should we replace local data with the server\'s?'
                )
            elif sync_approval == 'yes' or sync_approval == 'unknown' and create_new:
                logger.debug('User approved data sync from server')
                if self.sync_data_from_server():
                    if create_new:
                        # if we succesfully synced data from the server and this is
                        # a new account, make sure the api keys are properly stored
                        # in the DB
                        self.data.db.set_rotkehlchen_premium(api_key, api_secret)
            else:
                logger.debug('Could sync data from server but user refused')

    def unlock_user(self, user, password, create_new, sync_approval, api_key, api_secret):
        # unlock or create the DB
        self.password = password
        user_dir = self.data.unlock(user, password, create_new)
        self.try_premium_at_start(api_key, api_secret, create_new, sync_approval, user_dir)

        secret_data = self.data.db.get_exchange_secrets()
        self.cache_data_filename = os.path.join(self.data_dir, 'cache_data.json')
        historical_data_start = self.data.historical_start_date()
        self.trades_historian = TradesHistorian(
            self.data_dir,
            self.data.db,
            self.data.get_eth_accounts(),
            historical_data_start,
        )
        self.price_historian = PriceHistorian(
            self.data_dir,
            historical_data_start,
        )
        self.accountant = Accountant(
            price_historian=self.price_historian,
            profit_currency=self.data.main_currency(),
            create_csv=True
        )

        self.inquirer = Inquirer(kraken=self.kraken)
        self.initialize_exchanges(secret_data)

        self.blockchain = Blockchain(
            self.data.db.get_blockchain_accounts(),
            self.data.eth_tokens,
            self.data.db.get_owned_tokens(),
            self.inquirer,
            self.args.ethrpc_port
        )

    def set_premium_credentials(self, api_key, api_secret):
        if hasattr(self, 'premium'):
            valid, empty_or_error = self.premium.set_credentials(api_key, api_secret)
        else:
            self.premium, valid, empty_or_error = premium_create_and_verify(api_key, api_secret)

        if valid:
            self.data.set_premium_credentials(api_key, api_secret)
            return True, ''
        return False, empty_or_error

    def maybe_upload_data_to_server(self):
        logger.debug('Maybe upload to server')
        # upload only if unlocked user has premium
        if not hasattr(self, 'premium'):
            return

        # upload only once per hour
        diff = ts_now() - self.last_data_upload_ts
        if diff > 3600:
            self.upload_data_to_server()

    def upload_data_to_server(self):
        logger.debug('upload to server -- start')
        data, our_hash = self.data.compress_and_encrypt_db(self.password)
        success, result_or_error = self.premium.query_last_data_metadata()
        if not success:
            logger.debug('upload to server -- query last metadata error: {}'.format(result_or_error))
            return

        logger.debug("CAN_PUSH--> OURS: {} THEIRS: {}".format(our_hash, result_or_error['data_hash']))
        if our_hash == result_or_error['data_hash']:
            logger.debug('upload to server -- same hash')
            # same hash -- no need to upload anything
            return

        our_last_write_ts = self.data.db.get_last_write_ts()
        if our_last_write_ts <= result_or_error['last_modify_ts']:
            # Server's DB was modified after our local DB
            logger.debug("CAN_PUSH -> 3")
            logger.debug('upload to server -- remote db more recent than local')
            return

        success, result_or_error = self.premium.upload_data(
            data,
            our_hash,
            our_last_write_ts,
            'zlib'
        )
        if not success:
            logger.debug('upload to server -- upload error: {}'.format(result_or_error))
            return

        self.last_data_upload_ts = ts_now()
        logger.debug('upload to server -- success')

    def can_sync_data_from_server(self):
        logger.debug('sync data from server -- start')
        data, our_hash = self.data.compress_and_encrypt_db(self.password)
        success, result_or_error = self.premium.query_last_data_metadata()
        if not success:
            logger.debug('sync data from server-- error: {}'.format(result_or_error))
            return False

        logger.debug("CAN_PULL--> OURS: {} THEIRS: {}".format(our_hash, result_or_error['data_hash']))
        if our_hash == result_or_error['data_hash']:
            logger.debug('sync from server -- same hash')
            # same hash -- no need to get anything
            return False

        our_last_write_ts = self.data.db.get_last_write_ts()
        if our_last_write_ts >= result_or_error['last_modify_ts']:
            # Local DB is newer than Server DB
            logger.debug('sync from server -- local DB more recent than remote')
            return False

        return True

    def sync_data_from_server(self):
        success, error_or_result = self.premium.pull_data()
        if not success:
            logger.debug('sync from server -- pulling error {}'.format(error_or_result))
            return False

        self.data.decompress_and_decrypt_db(self.password, error_or_result['data'])
        return True

    def start(self):
        return gevent.spawn(self.main_loop)

    def main_loop(self):
        while True and not self.shutdown_event.is_set():
            logger.debug('Main loop start')
            if self.poloniex is not None:
                self.poloniex.main_logic()
            if self.kraken is not None:
                self.kraken.main_logic()

            self.maybe_upload_data_to_server()

            logger.debug('Main loop end')
            gevent.sleep(MAIN_LOOP_SECS_DELAY)

    def process_history(self, start_ts, end_ts):
        history, margin_history, loan_history, asset_movements, eth_transactions = self.trades_historian.get_history(
            start_ts=0,  # For entire history processing we need to have full history available
            end_ts=ts_now(),
            end_at_least_ts=end_ts
        )
        return self.accountant.process_history(
            start_ts,
            end_ts,
            history,
            margin_history,
            loan_history,
            asset_movements,
            eth_transactions
        )

    def query_fiat_balances(self):
        result = {}
        balances = self.data.get_fiat_balances()
        for currency, amount in balances.items():
            amount = FVal(amount)
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

        result = self.blockchain.query_balances()['totals']
        if result != {}:
            balances['blockchain'] = result

        result = self.query_fiat_balances()
        if result != {}:
            balances['banks'] = result

        combined = combine_stat_dicts([v for k, v in balances.items()])
        total_usd_per_location = [(k, dict_get_sumof(v, 'usd_value')) for k, v in balances.items()]

        # calculate net usd value
        net_usd = FVal(0)
        for k, v in combined.items():
            net_usd += FVal(v['usd_value'])

        stats = {
            'location': {
            },
            'net_usd': net_usd
        }
        for entry in total_usd_per_location:
            name = entry[0]
            total = entry[1]
            stats['location'][name] = {
                'usd_value': total,
                'percentage_of_net_value': (total / net_usd).to_percentage(),
            }

        for k, v in combined.items():
            combined[k]['percentage_of_net_value'] = (v['usd_value'] / net_usd).to_percentage()

        result_dict = merge_dicts(combined, stats)

        if save_data:
            self.data.save_balances_data(result_dict)

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

    def set_main_currency(self, currency):
        with self.lock:
            self.data.set_main_currency(currency, self.accountant)
            if currency != 'USD':
                self.usd_to_main_currency_rate = query_fiat_pair('USD', currency)

    def set_settings(self, settings):
        with self.lock:
            self.data.set_settings(settings)
            main_currency = settings['main_currency']
            if main_currency != 'USD':
                self.usd_to_main_currency_rate = query_fiat_pair('USD', main_currency)

    def usd_to_main_currency(self, amount):
        main_currency = self.data.main_currency()
        if main_currency != 'USD' and not hasattr(self, 'usd_to_main_currency_rate'):
            self.usd_to_main_currency_rate = query_fiat_pair('USD', main_currency)

        return self.usd_to_main_currency_rate * amount

    def get_settings(self):
        return self.data.settings

    def setup_exchange(self, name, api_key, api_secret):
        if name not in SUPPORTED_EXCHANGES:
            return False, 'Attempted to register unsupported exchange {}'.format(name)

        if getattr(self, name) is not None:
            return False, 'Exchange {} is already registered'.format(name)

        secret_data = {}
        secret_data[name] = {
            'api_key': api_key,
            'api_secret': api_secret,
        }
        self.initialize_exchanges(secret_data)

        exchange = getattr(self, name)
        result, message = exchange.validate_api_key()
        if not result:
            self.delete_exchange_data(name)
            return False, message

        # Success, save the result in the DB
        self.data.db.add_exchange(name, api_key, api_secret)
        return True, ''

    def delete_exchange_data(self, name):
        self.connected_exchanges.remove(name)
        self.trades_historian.set_exchange(name, None)
        delattr(self, name)
        setattr(self, name, None)

    def remove_exchange(self, name):
        if getattr(self, name) is None:
            return False, 'Exchange {} is not registered'.format(name)

        self.delete_exchange_data(name)
        # Success, remove it also from the DB
        self.data.db.remove_exchange(name)
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
    r = Rotkehlchen(args)
