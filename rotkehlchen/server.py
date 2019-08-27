# Based on https://github.com/fyears/electron-python-example
from __future__ import print_function

import logging
import os
import signal
import traceback
from typing import Any, Dict, List, Union, cast

import gevent
import zerorpc
from gevent.event import Event
from gevent.lock import Semaphore

from rotkehlchen.args import app_args
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import (
    AuthenticationError,
    DeserializationError,
    IncorrectApiKeyFormat,
    RemoteError,
    RotkehlchenPermissionError,
    UnknownAsset,
)
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.typing import FiatAsset, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import simple_result
from rotkehlchen.utils.serialization import pretty_json_dumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer():
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

    @staticmethod
    def get_fiat_exchange_rates(currencies: List[str]):
        fiat_currencies = cast(List[FiatAsset], currencies)
        rates = Inquirer().get_fiat_usd_exchange_rates(fiat_currencies)
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
        msg = ''
        result = False
        try:
            self.rotkehlchen.set_premium_credentials(api_key, api_secret)
            result = True
        except (AuthenticationError, IncorrectApiKeyFormat) as e:
            msg = str(e)
        return {'result': result, 'message': msg}

    def set_premium_option_sync(self, should_sync):
        self.rotkehlchen.data.db.update_premium_sync(should_sync)
        return True

    def query_exchange_balances(self, name):
        res = {'name': name}
        exchange_obj = self.rotkehlchen.exchange_manager.connected_exchanges.get(name, None)
        if not exchange_obj:
            res['error'] = f'Could not query balances for {name} since it is not registered'
            return process_result(res)

        balances, msg = exchange_obj.query_balances()
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

    def query_netvalue_data(self):
        res = self.rotkehlchen.data.db.get_netvalue_data()
        result = {'times': res[0], 'data': res[1]}
        return process_result(result)

    def query_timed_balances_data(self, given_asset: str, start_ts: int, end_ts: int) -> Dict:
        try:
            start_ts = deserialize_timestamp(start_ts)
            end_ts = deserialize_timestamp(end_ts)
            asset = Asset(given_asset)
        except (UnknownAsset, DeserializationError) as e:
            return {'result': False, 'message': str(e)}

        res = self.rotkehlchen.data.db.query_timed_balances(
            from_ts=start_ts,
            to_ts=end_ts,
            asset=asset,
        )
        result = {'result': res, 'message': ''}
        return process_result(result)

    def query_owned_assets(self):
        res = self.rotkehlchen.data.db.query_owned_assets()
        result = {'result': res, 'message': ''}
        return process_result(result)

    def query_latest_location_value_distribution(self):
        res = self.rotkehlchen.data.db.get_latest_location_value_distribution()
        result = {'result': res, 'message': ''}
        return process_result(result)

    def query_latest_asset_value_distribution(self):
        res = self.rotkehlchen.data.db.get_latest_asset_value_distribution()
        result = {'result': res, 'message': ''}
        return process_result(result)

    def consume_messages(self):
        """Consumes all errors and warnings from the messages aggregator"""
        warnings = self.rotkehlchen.msg_aggregator.consume_warnings()
        errors = self.rotkehlchen.msg_aggregator.consume_errors()
        result = {'result': {'warnings': warnings, 'errors': errors}, 'message': ''}
        return process_result(result)

    def query_statistics_renderer(self):
        result_dict = {'result': '', 'message': 'user does not have premium'}
        if not self.rotkehlchen.premium:
            return process_result(result_dict)

        active = self.rotkehlchen.premium.is_active()
        if not active:
            return process_result(result_dict)

        try:
            result = self.rotkehlchen.premium.query_statistics_renderer()
            result_dict['result'] = result
            result_dict['message'] = ''
        except RemoteError as e:
            result_dict['message'] = str(e)

        return process_result(result_dict)

    def set_fiat_balance(self, currency: str, balance: str):
        result, message = self.rotkehlchen.data.set_fiat_balance(currency, balance)
        return {'result': result, 'message': message}

    def query_trade_history(self, location: str, start_ts: int, end_ts: int):
        """Queries the trades/margin position history of a single or all exchanges

        Note: This will only query trades/margin position history. Nothing else.
        Not loans, deposit/withdrawals e.t.c.
        """
        start_ts = Timestamp(start_ts)
        end_ts = Timestamp(end_ts)
        if location == 'all':
            (
                empty_or_error,
                history,
                _,
                _,
                _,
            ) = self.rotkehlchen.trades_historian.get_history(start_ts, end_ts)
            if empty_or_error != '':
                return process_result({'result': '', 'message': empty_or_error})
            # Ignore everything except for trades
            return process_result({'result': history, 'message': ''})

        if location not in SUPPORTED_EXCHANGES:
            return {
                'result': '',
                'message': f'Unknown exchange {location} provided in query_trade_history',
            }

        exchange = self.rotkehlchen.exchange_manager.connected_exchanges.get(location, None)
        if not exchange:
            msg = (
                f'Exchange {location} provided in query_trade_history is not '
                f'registered yet for this user'
            )
            return {'result': '', 'message': msg}

        result = exchange.query_trade_history(start_ts, end_ts, end_ts)
        return process_result({'result': result, 'message': ''})

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
        res = self.query_async('query_balances', save_data=save_data)
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

    def add_blockchain_account(self, given_blockchain: str, given_account: str):
        try:
            blockchain = SupportedBlockchain(given_blockchain)
        except ValueError:
            msg = f'Tried to add blockchain account for unsupported blockchain {given_blockchain}'
            return simple_result(False, msg)
        return self.rotkehlchen.add_blockchain_account(blockchain, given_account)

    def remove_blockchain_account(self, given_blockchain: str, given_account: str):
        try:
            blockchain = SupportedBlockchain(given_blockchain)
        except ValueError:
            msg = (
                f'Tried to remove blockchain account for unsupported blockchain {given_blockchain}'
            )
            return simple_result(False, msg)
        return self.rotkehlchen.remove_blockchain_account(blockchain, given_account)

    def get_ignored_assets(self):
        result = {
            'ignored_assets': [
                identifier for identifier in self.rotkehlchen.data.db.get_ignored_assets()
            ],
        }
        return process_result(result)

    def add_ignored_asset(self, asset: str):
        result, message = self.rotkehlchen.data.add_ignored_asset(asset)
        return {'result': result, 'message': message}

    def remove_ignored_asset(self, asset: str):
        result, message = self.rotkehlchen.data.remove_ignored_asset(asset)
        return {'result': result, 'message': message}

    def unlock_user(
            self,
            user: str,
            password: str,
            create_new: Union[bool, str],
            sync_approval: str,
            api_key: str,
            api_secret: str,
    ) -> Dict[str, Any]:
        """Either unlock an existing user or create a new one"""
        res = {'result': True, 'message': ''}

        assert isinstance(sync_approval, str), "sync_approval should be a string"
        assert isinstance(api_key, str), "api_key should be a string"
        assert isinstance(api_secret, str), "api_secret should be a string"

        if not isinstance(create_new, bool):
            if not isinstance(create_new, str):
                raise ValueError('create_new can only be boolean or str')

            if create_new in ('False', 'false', 'FALSE'):
                create_new = False
            elif create_new in ('True', 'true', 'TRUE'):
                create_new = True
            else:
                raise ValueError(f'Invalid string value for create_new {create_new}')

        valid_actions = ['unknown', 'yes', 'no']
        if sync_approval not in valid_actions:
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
            res['exchanges'] = self.rotkehlchen.exchange_manager.get_connected_exchange_names()
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

    def main(self):
        if os.name != 'nt':
            gevent.hub.signal(signal.SIGQUIT, self.shutdown)
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        self.zerorpc = zerorpc.Server(self)
        addr = 'tcp://127.0.0.1:' + str(self.port())
        self.zerorpc.bind(addr)
        print('start running on {}'.format(addr))
        self.zerorpc_greenlet = gevent.spawn(self.zerorpc.run)
        self.stop_event.wait()
