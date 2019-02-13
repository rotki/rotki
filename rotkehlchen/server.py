# Based on https://github.com/fyears/electron-python-example
from __future__ import print_function

import logging
import signal
import traceback

import gevent
import zerorpc
from gevent.event import Event
from gevent.lock import Semaphore

from rotkehlchen.args import app_args
from rotkehlchen.errors import AuthenticationError, RotkehlchenPermissionError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.utils import pretty_json_dumps, process_result

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer(object):
    def __init__(self):
        arg_parser = app_args(
            prog='rotkehlchen',
            description='Rotkehlchen Crypto Portfolio Management',
        )
        self.args = arg_parser.parse_args()
        self.rotkehlchen = Rotkehlchen(self.args)
        self.stop_event = Event()
        mainloop_greenlet = self.rotkehlchen.start()
        mainloop_greenlet.link_exception(self.handle_killed_greenlets)
        # Greenlets that will be waited for when we shutdown
        self.waited_greenlets = [mainloop_greenlet]
        # Greenlets that can be killed instead of waited for when we shutdown
        self.killable_greenlets = []
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
        log.debug('Shutdown initiated')
        self.zerorpc.stop()
        self.rotkehlchen.shutdown()
        log.debug('Waiting for greenlets')
        gevent.wait(self.waited_greenlets)
        log.debug('Waited for greenlets. Killing all other greenlets')
        gevent.killall(self.killable_greenlets)
        log.debug('Greenlets killed. Killing zerorpc greenlet')
        self.zerorpc_greenlet.kill()
        log.debug('Killed zerorpc greenlet')
        log.debug('Shutdown completed')
        logging.shutdown()
        self.stop_event.set()

    def logout(self):
        # Kill all queries apart from the main loop -- perhaps a bit heavy handed
        # but the other options would be:
        # 1. to wait for all of them. That could take a lot of time, for no reason.
        #    All results would be discarded anyway since we are logging out.
        # 2. Have an intricate stop() notification system for each greenlet, but
        #   that is going to get complicated fast.
        gevent.killall(self.killable_greenlets)
        with self.task_lock:
            self.task_results = {}
        self.rotkehlchen.logout()

    def set_main_currency(self, currency_text):
        self.rotkehlchen.set_main_currency(currency_text)

    def set_settings(self, settings):
        result, message = self.rotkehlchen.set_settings(settings)
        return {'result': result, 'message': message}

    def get_total_in_usd(self, balances):
        total = 0
        for _, entry in balances.items():
            total += entry['usd_value']

        return total

    def handle_killed_greenlets(self, greenlet):
        if not greenlet.exception:
            log.warning('handle_killed_greenlets without an exception')
            return

        log.error(
            'Greenlet for task {} dies with exception: {}.\n'
            'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
            .format(
                greenlet.task_id,
                greenlet.exception,
                greenlet.exc_info[0],
                greenlet.exc_info[1],
                ''.join(traceback.format_tb(greenlet.exc_info[2])),
            ))
        # also write an error for the task result
        result = {
            'error': str(greenlet.exception),
        }
        self.write_task_result(greenlet.task_id, result)

    def _query_async(self, command, task_id, **kwargs):
        result = getattr(self, command)(**kwargs)
        self.write_task_result(task_id, result)

    def query_async(self, command, **kwargs):
        task_id = self.new_task_id()
        log.debug("NEW TASK {} (kwargs:{}) with ID: {}".format(command, kwargs, task_id))
        greenlet = gevent.spawn(
            self._query_async,
            command,
            task_id,
            **kwargs,
        )
        greenlet.task_id = task_id
        greenlet.link_exception(self.handle_killed_greenlets)
        self.killable_greenlets.append(greenlet)
        return task_id

    def query_task_result(self, task_id):
        with self.task_lock:
            len1 = len(self.task_results)
            ret = self.task_results.pop(int(task_id), None)
            if not ret and len1 != len(self.task_results):
                log.error("Popped None from results task but lost an entry")
            if ret:
                log.debug("Found response for task {}".format(task_id))
        return ret

    def get_fiat_exchange_rates(self, currencies):
        rates = self.rotkehlchen.inquirer.get_fiat_usd_exchange_rates(currencies)
        res = {'exchange_rates': rates}
        return process_result(res)

    def get_settings(self):
        return process_result(self.rotkehlchen.data.db.get_settings())

    def remove_exchange(self, name):
        result, message = self.rotkehlchen.remove_exchange(name)
        return {'result': result, 'message': message}

    def setup_exchange(self, name, api_key, api_secret):
        result, message = self.rotkehlchen.setup_exchange(name, api_key, api_secret)
        return {'result': result, 'message': message}

    def query_otctrades(self):
        trades = self.rotkehlchen.data.get_external_trades()
        result = {'result': trades, 'message': ''}
        return process_result(result)

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
        res = {'name': name}
        balances, msg = getattr(self.rotkehlchen, name).query_balances()
        if balances is None:
            res['error'] = msg
        else:
            res['balances'] = balances

        return process_result(res)

    def query_exchange_balances_async(self, name):
        res = self.query_async('query_exchange_balances', name=name)
        return {'task_id': res}

    def query_blockchain_balances(self):
        result, empty_or_error = self.rotkehlchen.blockchain.query_balances()
        return process_result({'result': result, 'message': empty_or_error})

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

        return process_result(exchange.query_trade_history(start_ts, end_ts, end_ts))

    def process_trade_history(self, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        result, error_or_empty = self.rotkehlchen.process_history(start_ts, end_ts)
        response = {'result': result, 'message': error_or_empty}
        return process_result(response)

    def process_trade_history_async(self, start_ts, end_ts):
        res = self.query_async('process_trade_history', start_ts=start_ts, end_ts=end_ts)
        return {'task_id': res}

    def export_processed_history_csv(self, dirpath):
        result, message = self.rotkehlchen.accountant.csvexporter.create_files(dirpath)
        return {'result': result, 'message': message}

    def query_balances(self, save_data=False):
        if isinstance(save_data, str) and (save_data == 'save' or save_data == 'True'):
            save_data = True

        result = self.rotkehlchen.query_balances(save_data)
        print(pretty_json_dumps(result))
        return process_result(result)

    def query_balances_async(self, save_data=False):
        res = self.query_async('query_balances')
        return {'task_id': res}

    def query_periodic_data(self):
        """Will query for some client data that can change frequently"""
        result = self.rotkehlchen.query_periodic_data()
        return process_result(result)

    def get_eth_tokens(self):
        result = {
            'all_eth_tokens': self.rotkehlchen.data.eth_tokens,
            'owned_eth_tokens': self.rotkehlchen.blockchain.eth_tokens,
        }
        return process_result(result)

    def add_owned_eth_tokens(self, tokens):
        return self.rotkehlchen.add_owned_eth_tokens(tokens)

    def remove_owned_eth_tokens(self, tokens):
        return self.rotkehlchen.remove_owned_eth_tokens(tokens)

    def add_blockchain_account(self, blockchain, account):
        return self.rotkehlchen.add_blockchain_account(blockchain, account)

    def remove_blockchain_account(self, blockchain, account):
        return self.rotkehlchen.remove_blockchain_account(blockchain, account)

    def get_ignored_assets(self):
        result = {
            'ignored_assets': self.rotkehlchen.data.db.get_ignored_assets(),
        }
        return result

    def add_ignored_asset(self, asset):
        result, message = self.rotkehlchen.data.add_ignored_asset(asset)
        return {'result': result, 'message': message}

    def remove_ignored_asset(self, asset):
        result, message = self.rotkehlchen.data.remove_ignored_asset(asset)
        return {'result': result, 'message': message}

    def unlock_user(self, user, password, create_new, sync_approval, api_key, api_secret):
        """Either unlock an existing user or create a new one"""
        res = {'result': True, 'message': ''}

        assert isinstance(sync_approval, str), "sync_approval should be a string"
        assert isinstance(api_key, str), "api_key should be a string"
        assert isinstance(api_secret, str), "api_secret should be a string"

        valid_actions = ['unknown', 'yes', 'no']
        valid_approve = isinstance(sync_approval, str) and sync_approval in valid_actions
        if not valid_approve:
            raise ValueError('Provided invalid value for sync_approval')

        if api_key != '' and create_new is False:
            raise ValueError('Should not ever have api_key provided during a normal login')

        if api_key != '' and api_secret == '' or api_secret != '' and api_key == '':
            raise ValueError('Must provide both or neither of api key/secret')

        try:
            self.rotkehlchen.unlock_user(
                user,
                password,
                create_new,
                sync_approval,
                api_key,
                api_secret,
            )
            res['exchanges'] = self.rotkehlchen.connected_exchanges
            res['premium'] = self.rotkehlchen.premium is not None
            res['settings'] = self.rotkehlchen.data.db.get_settings()
        except AuthenticationError as e:
            res['result'] = False
            res['message'] = str(e)
        except RotkehlchenPermissionError as e:
            res['result'] = False
            res['permission_needed'] = True
            res['message'] = str(e)

        return res

    def echo(self, text):
        return text

    def main(self):
        gevent.hub.signal(signal.SIGQUIT, self.shutdown)
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        # self.zerorpc = zerorpc.Server(self, heartbeat=15)
        self.zerorpc = zerorpc.Server(self)
        addr = 'tcp://127.0.0.1:' + str(self.port())
        self.zerorpc.bind(addr)
        print('start running on {}'.format(addr))
        self.zerorpc_greenlet = gevent.spawn(self.zerorpc.run)
        self.stop_event.wait()
