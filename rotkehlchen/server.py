# Based on https://github.com/fyears/electron-python-example
from __future__ import print_function

import gevent
from gevent.event import Event
from gevent.lock import Semaphore
import signal
import zerorpc
import pickle
import traceback

from rotkehlchen.fval import FVal
from rotkehlchen.errors import InputError, AuthenticationError, PermissionError
from rotkehlchen.args import app_args
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.utils import pretty_json_dumps
from rotkehlchen.inquirer import get_fiat_usd_exchange_rates

import logging
logger = logging.getLogger(__name__)


def _process_entry(entry):
    if isinstance(entry, FVal):
        return str(entry)
    elif isinstance(entry, list):
        new_list = list()
        for new_entry in entry:
            new_list.append(_process_entry(new_entry))
        return new_list
    elif isinstance(entry, dict):
        new_dict = dict()
        for k, v in entry.items():
            new_dict[k] = _process_entry(v)
        return new_dict
    else:
        return entry


def process_result(result):
    """Before sending out a result a dictionary via the server we are turning
    all Decimals to strings so that the serialization to float/big number is handled
    by the client application and we lose nothing in the transfer"""
    return _process_entry(result)


def simple_result(v, msg):
    return {'result': v, 'message': msg}


def accounts_result(per_account, totals):
    result = {
        'result': True,
        'message': '',
        'per_account': per_account,
        'totals': totals
    }
    return process_result(result)


class RotkehlchenServer(object):
    def __init__(self):
        self.args = app_args()
        self.rotkehlchen = Rotkehlchen(self.args)
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self.handle_killed_greenlets)
        self.greenlets = [mainloop_greenlet]
        self.task_lock = Semaphore()
        self.task_id = 0
        self.task_results = {}

    def new_task_id(self):
        with self.task_lock:
            task_id = self.task_id
            self.task_id += 1
        return task_id

    def write_task_result(self, task_id, result):
        with self.task_lock:
            self.task_results[task_id] = result

    def get_task_result(self, task_id):
        with self.task_lock:
            return self.task_results[task_id]

    def port(self):
        return self.args.zerorpc_port

    def shutdown(self):
        logger.debug('Shutdown initiated')
        self.zerorpc.stop()
        gevent.wait(self.greenlets)
        self.rotkehlchen.shutdown()
        print("Shutting down zerorpc server")
        logger.debug('Shutdown completed')
        logging.shutdown()

    def set_main_currency(self, currency_text):
        self.rotkehlchen.set_main_currency(currency_text)

    def set_settings(self, settings):
        self.rotkehlchen.set_settings(settings)
        return True

    def get_total_in_usd(self, balances):
        total = 0
        for _, entry in balances.items():
            total += entry['usd_value']

        return total

    def handle_killed_greenlets(self, greenlet):
        if greenlet.exception:
            logger.error(
                'Greenlet for task {} dies with exception: {}.\n'
                'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
                .format(
                    greenlet.task_id,
                    greenlet.exception,
                    greenlet._exc_info[0],
                    greenlet._exc_info[1],
                    ''.join(traceback.format_tb(pickle.loads(greenlet._exc_info[2]))),
                ))
            # also write an error for the task result
            result = {
                'error': str(greenlet.exception)
            }
            self.write_task_result(greenlet.task_id, result)

    def _query_async(self, command, task_id, **kwargs):
        result = getattr(self, command)(**kwargs)
        self.write_task_result(task_id, result)

    def query_async(self, command, **kwargs):
        task_id = self.new_task_id()
        logger.debug("NEW TASK {} (kwargs:{}) with ID: {}".format(command, kwargs, task_id))
        greenlet = gevent.spawn(
            self._query_async,
            command,
            task_id,
            **kwargs
        )
        greenlet.task_id = task_id
        greenlet.link_exception(self.handle_killed_greenlets)
        self.greenlets.append(greenlet)
        return task_id

    def query_task_result(self, task_id):
        logger.debug("Querying task result with task id {}".format(task_id))
        with self.task_lock:
            len1 = len(self.task_results)
            ret = self.task_results.pop(int(task_id), None)
            if not ret and len1 != len(self.task_results):
                logger.error("Popped None from results task but lost an entry")
            if ret:
                logger.debug("Found response for task {}".format(task_id))
        return ret

    def get_fiat_exchange_rates(self, currencies):
        res = {'exchange_rates': get_fiat_usd_exchange_rates(currencies)}
        return process_result(res)

    def get_settings(self):
        settings = self.rotkehlchen.get_settings()
        res = {
            'main_currency': self.rotkehlchen.data.main_currency(),
            'ui_floating_precision': settings['ui_floating_precision'],
            'historical_data_start_date': settings['historical_data_start_date'],
        }
        return process_result(res)

    def remove_exchange(self, name):
        result, message = self.rotkehlchen.remove_exchange(name)
        return {'result': result, 'message': message}

    def setup_exchange(self, name, api_key, api_secret):
        result, message = self.rotkehlchen.setup_exchange(name, api_key, api_secret)
        return {'result': result, 'message': message}

    def query_otctrades(self):
        trades = self.rotkehlchen.data.get_external_trades()
        return process_result(trades)

    def add_otctrade(self, data):
        result, message = self.rotkehlchen.data.add_external_trade(data)
        return {'result': result, 'message': message}

    def edit_otctrade(self, data):
        result, message = self.rotkehlchen.data.edit_external_trade(data)
        return {'result': result, 'message': message}

    def delete_otctrade(self, trade_id):
        result, message = self.rotkehlchen.data.delete_external_trade(trade_id)
        return {'result': result, 'message': message}

    def set_premium_credentials(self, api_key, api_secret):
        result, empty_or_error = self.rotkehlchen.set_premium_credentials(api_key, api_secret)
        return {'result': result, 'message': empty_or_error}

    def set_premium_option_sync(self, should_sync):
        self.rotkehlchen.data.db.update_premium_sync(should_sync)
        return True

    def query_exchange_balances(self, name):
        balances = getattr(self.rotkehlchen, name).query_balances()
        res = {
            'name': name,
            'balances': balances
        }
        return process_result(res)

    def query_exchange_balances_async(self, name):
        res = self.query_async('query_exchange_balances', name=name)
        return {'task_id': res}

    def query_blockchain_balances(self):
        balances = self.rotkehlchen.blockchain.query_balances()
        return process_result(balances)

    def query_blockchain_balances_async(self):
        res = self.query_async('query_blockchain_balances')
        return {'task_id': res}

    def query_fiat_balances(self):
        res = self.rotkehlchen.query_fiat_balances()
        return process_result(res)

    def set_fiat_balance(self, currency, balance):
        result, message = self.rotkehlchen.data.set_fiat_balance(currency, balance)
        return {'result': result, 'message': message}

    def query_trade_history(self, location, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        if location == 'all':
            return self.rotkehlchen.trades_historian.get_history(start_ts, end_ts)

        try:
            exchange = getattr(self.rotkehlchen, location)
        except AttributeError:
            raise "Unknown location {} given".format(location)

        return exchange.query_trade_history(start_ts, end_ts)

    def query_asset_price(self, from_asset, to_asset, timestamp):
        price = self.rotkehlchen.data.accountant.query_historical_price(
            from_asset, to_asset, int(timestamp)
        )

        return str(price)

    def process_trade_history(self, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        result = self.rotkehlchen.process_history(start_ts, end_ts)
        return process_result(result)

    def process_trade_history_async(self, start_ts, end_ts):
        res = self.query_async('process_trade_history', start_ts=start_ts, end_ts=end_ts)
        return {'task_id': res}

    def query_balances(self, save_data=False):
        if isinstance(save_data, str) and (save_data == 'save' or save_data == 'True'):
            save_data = True

        result = self.rotkehlchen.query_balances(save_data)
        print(pretty_json_dumps(result))
        return process_result(result)

    def query_balances_async(self, save_data=False):
        res = self.query_async('query_balances')
        return {'task_id': res}

    def get_eth_tokens(self):
        result = {
            'all_eth_tokens': self.rotkehlchen.data.eth_tokens,
            'owned_eth_tokens': self.rotkehlchen.blockchain.eth_tokens
        }
        return process_result(result)

    def add_owned_eth_tokens(self, tokens):
        try:
            new_data = self.rotkehlchen.blockchain.track_new_tokens(tokens)
        except InputError as e:
            return simple_result(False, str(e))

        self.rotkehlchen.data.write_owned_eth_tokens(self.rotkehlchen.blockchain.owned_eth_tokens)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def remove_owned_eth_tokens(self, tokens):
        try:
            new_data = self.rotkehlchen.blockchain.remove_eth_tokens(tokens)
        except InputError as e:
            return simple_result(False, str(e))
        self.rotkehlchen.data.write_owned_eth_tokens(self.rotkehlchen.blockchain.owned_eth_tokens)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def add_blockchain_account(self, blockchain, account):
        try:
            new_data = self.rotkehlchen.blockchain.add_blockchain_account(blockchain, account)
        except InputError as e:
            return simple_result(False, str(e))
        self.rotkehlchen.data.add_blockchain_account(blockchain, account)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def remove_blockchain_account(self, blockchain, account):
        try:
            new_data = self.rotkehlchen.blockchain.remove_blockchain_account(blockchain, account)
        except InputError as e:
            return simple_result(False, str(e))
        self.rotkehlchen.data.remove_blockchain_account(blockchain, account)
        return accounts_result(new_data['per_account'], new_data['totals'])

    def unlock_user(self, user, password, create_new, sync_approval, api_key, api_secret):
        """Either unlock an existing user or create a new one"""
        res = {'result': True, 'message': ''}

        assert isinstance(sync_approval, str), "sync_approval should be a string"
        assert isinstance(api_key, str), "api_key should be a string"
        assert isinstance(api_secret, str), "api_secret should be a string"

        valid_approve = isinstance(sync_approval, str) and sync_approval in ['unknown', 'yes', 'no']
        if not valid_approve:
            raise ValueError('Provided invalid value for sync_approval')

        if api_key != '' and create_new is False:
            raise ValueError('Should not ever have api_key provided during a normal login')

        if api_key != '' and api_secret == '' or api_secret != '' and api_key == '':
            raise ValueError('Must provide both or neither of api key/secret')

        try:
            self.rotkehlchen.unlock_user(user, password, create_new, sync_approval, api_key, api_secret)
            res['exchanges'] = self.rotkehlchen.connected_exchanges
            res['premium'] = True if hasattr(self.rotkehlchen, 'premium') else False
            res['settings'] = self.rotkehlchen.data.db.get_settings()
        except AuthenticationError as e:
            res['result'] = False
            res['message'] = str(e)
        except PermissionError as e:
            res['result'] = False
            res['permission_needed'] = True
            res['message'] = str(e)

        return res

    def echo(self, text):
        return text

    def main(self):
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        # self.zerorpc = zerorpc.Server(self, heartbeat=15)
        self.zerorpc = zerorpc.Server(self)
        addr = 'tcp://127.0.0.1:' + str(self.port())
        self.zerorpc.bind(addr)
        print('start running on {}'.format(addr))
        self.zerorpc.run()
