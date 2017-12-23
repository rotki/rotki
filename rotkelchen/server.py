# Based on https://github.com/fyears/electron-python-example
from __future__ import print_function

import gevent
from gevent.event import Event
from gevent.lock import Semaphore
import signal
import zerorpc

from rotkelchen.fval import FVal
from rotkelchen.args import app_args
from rotkelchen.rotkelchen import Rotkelchen
from rotkelchen.utils import pretty_json_dumps
from rotkelchen.transactions import query_txlist

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


class RotkelchenServer(object):
    def __init__(self):
        self.args = app_args()
        self.rotkelchen = Rotkelchen(self.args)
        self.stop_event = Event()
        mainloop_greenlet = self.rotkelchen.start()
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
        logger.debug('Writting task result for task id {}. It\'s {}'.format(task_id, result))
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
        self.rotkelchen.shutdown()
        print("Shutting down zerorpc server")
        logger.debug('Shutdown completed')
        logging.shutdown()

    def set_main_currency(self, currency_text):
        self.rotkelchen.set_main_currency(currency_text)

    def get_total_in_main_currency(self, balances):
        total = 0
        for _, entry in balances.items():
            total += entry['usd_value']

        return self.rotkelchen.usd_to_main_currency(total)

    def handle_killed_greenlets(self, greenlet):
        if greenlet.exception:
            logger.error('Greenlet dies with exception: {}'.format(greenlet.exception))

    def _query_async(self, command, task_id, **kwargs):
        result = getattr(self, command)(**kwargs)
        self.write_task_result(task_id, result)

    def query_async(self, command, **kwargs):
        task_id = self.new_task_id()
        logger.debug("NEW TASK {} with ID: {}".format(command, task_id))
        greenlet = gevent.spawn(
            self._query_async,
            command,
            task_id,
            **kwargs
        )
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
                logger.debug("Found response for task {} and it is {}".format(task_id, ret))
        return ret

    # def get_registered_exchanges(self):
    def get_initial_settings(self):
        res = {
            'exchanges': self.rotkelchen.get_exchanges(),
            'main_currency': self.rotkelchen.main_currency
        }
        return process_result(res)

    def query_exchange_total(self, name, first_time):
        logger.debug("Query exchange {} called.".format(name))
        if first_time:
            getattr(self.rotkelchen, name).first_connection()
        balances = getattr(self.rotkelchen, name).query_balances()
        res = {
            'name': name,
            'total': self.get_total_in_main_currency(balances)
        }
        logger.debug("Query exchange {} finished.".format(name))
        return process_result(res)

    def query_exchange_total_async(self, name, first_time):
        res = self.query_async('query_exchange_total', name=name, first_time=first_time)
        return {'task_id': res}

    def query_blockchain_total(self):
        balances = self.rotkelchen.query_blockchain_balances()
        res = {'total': self.get_total_in_main_currency(balances)}
        return process_result(res)

    def query_blockchain_total_async(self):
        res = self.query_async('query_blockchain_total')
        return {'task_id': res}

    def query_banks_total(self):
        balances = self.rotkelchen.query_bank_balances()
        res = {'total': self.get_total_in_main_currency(balances)}
        logger.debug('At query_bank_balances end')
        return process_result(res)

    def query_banks_total_async(self):
        res = self.query_async('query_banks_total')
        return {'task_id': res}

    def query_trade_history(self, location, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        if location == 'all':
            return self.rotkelchen.data.trades_historian.get_history(start_ts, end_ts)

        try:
            exchange = getattr(self.rotkelchen, location)
        except:
            raise "Unknown location {} given".format(location)

        return exchange.query_trade_history(start_ts, end_ts)

    def query_asset_price(self, from_asset, to_asset, timestamp):
        price = self.rotkelchen.data.accountant.query_historical_price(
            from_asset, to_asset, int(timestamp)
        )

        return str(price)

    def process_trade_history(self, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        result = self.rotkelchen.process_history(start_ts, end_ts)

        print('process_trade_history() done')
        return process_result(result)

    def query_balances(self, save_data=False):
        if isinstance(save_data, str) and (save_data == 'save' or save_data == 'True'):
            save_data = True

        s = pretty_json_dumps(self.rotkelchen.query_balances(save_data))
        print(s)
        return s

    def plot(self):
        self.rotkelchen.plot()

    def extend_values(self, other_file_path):
        self.rotkelchen.extend_values(other_file_path)

    def test(self, from_csv):
        if from_csv == "True":
            from_csv = True
        elif from_csv == "False":
            from_csv = False
        else:
            raise ValueError("Illegal value {} for argument from_csv".format(from_csv))

        start_ts = 1451606400  # 01/01/2016
        end_ts = 1483228799  # 31/12/2016

        result = self.rotkelchen.poloniex.query_loan_history(
            start_ts,
            end_ts,
            from_csv=from_csv
        )
        from history import process_polo_loans
        result = process_polo_loans(result, start_ts, end_ts)

        # september_1st = 1472774399
        for loan in result:
            if loan['profit/loss'] < 0:
                print(loan)

        from utils import tsToDate
        print("Number of results returned {}".format(len(result)))
        print("First loan open/close_time: {} - {}".format(
            tsToDate(result[0]['open_time'], formatstr='%d/%m/%Y %H:%M:%S'),
            tsToDate(result[0]['close_time'], formatstr='%d/%m/%Y %H:%M:%S'),
        ))
        print("Second loan open/close_time: {} - {}".format(
            tsToDate(result[1]['open_time'], formatstr='%d/%m/%Y %H:%M:%S'),
            tsToDate(result[1]['close_time'], formatstr='%d/%m/%Y %H:%M:%S'),
        ))
        print("Last loan open/close_time: {} - {}".format(
            tsToDate(result[-1]['open_time'], formatstr='%d/%m/%Y %H:%M:%S'),
            tsToDate(result[-1]['close_time'], formatstr='%d/%m/%Y %H:%M:%S'),
        ))
        return True

    def test2(self):
        start_ts = 1451606400 # 01/01/2016
        end_ts = 1483228799 # 31/12/2016
        _, margin_trades, _, _ = self.rotkelchen.data.trades_historian.get_history(start_ts, end_ts, end_ts)
        total_buy = 0
        total_sell = 0
        # TODO you have to also sum up all fees and add them as loss

        first_long_end = 1472860799
        for trade in margin_trades:
            if trade.timestamp > first_long_end:
                break
            if trade.type == 'buy':
                total_buy += trade.cost
            elif trade.type == 'sell':
                total_sell += trade.cost
            else:
                raise ValueError('Unknown margin trade type {}'.format(trade.type))

        result = {
            'total_buy': total_buy,
            'total_sell': total_sell,
            'total_cost': total_sell - total_buy
        }
        return pretty_json_dumps(result)

    def test3(self):
        result = query_txlist("0xd1b8d347fd50dc7838a8ceb4294b6621b0b300f6", False)
        return pretty_json_dumps(result)

    def test4(self):
        result = self.rotkelchen.poloniex.query_balances()
        return pretty_json_dumps(result)

    def test5(self):
        result = self.rotkelchen.binance.query_trade_history()
        return pretty_json_dumps(result)

    def echo(self, text):
        return text

    def main(self):
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        self.zerorpc = zerorpc.Server(self)
        addr = 'tcp://127.0.0.1:' + str(self.port())
        self.zerorpc.bind(addr)
        print('start running on {}'.format(addr))
        self.zerorpc.run()
