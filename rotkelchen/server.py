# Based on https://github.com/fyears/electron-python-example

from __future__ import print_function
import traceback
import sys
import gevent
import signal

import zerorpc

from args import app_args
from rotkelchen import Rotkelchen
from utils import pretty_json_dumps
from transactions import query_txlist
from decimal import Decimal


def _process_entry(entry):
    if isinstance(entry, Decimal):
        return str(entry)
    elif isinstance(entry, list):
        new_list = list()
        for new_entry in entry:
            new_list.append(_process_entry(entry))
        return new_list
    elif isinstance(entry, dict):
        new_dict = dict()
        for k, v in entry.iteritems():
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

    def port(self):
        return self.args.zerorpc_port

    def shutdown(self):
        self.rotkelchen.shutdown()
        print("Shutting down zerorpc server")
        self.zerorpc.stop()

    def set_main_currency(self, currency_text):
        with self.rotkelchen.lock:
            self.rotkelchen.set_main_currency(currency_text)

    def get_total_in_main_currency(self, balances):
        total = 0
        for _, entry in balances.iteritems():
            total += entry['usd_value']

        return self.rotkelchen.usd_to_main_currency(total)

    # def get_registered_exchanges(self):
    def get_initial_settings(self):
        with self.rotkelchen.lock:
            return {
                'exchanges': self.rotkelchen.get_exchanges(),
                'main_currency': self.rotkelchen.main_currency
            }

    def query_exchange_total(self, name, first_time):
        with self.rotkelchen.lock:
            if first_time:
                getattr(self.rotkelchen, name).first_connection()
            balances = getattr(self.rotkelchen, name).query_balances(ignore_cache=True)
            return {
                'name': name,
                'total': self.get_total_in_main_currency(balances)
            }

    def query_blockchain_total(self):
        with self.rotkelchen.lock:
            balances = self.rotkelchen.query_blockchain_balances()
            return {
                'total': self.get_total_in_main_currency(balances)
            }

    def query_banks_total(self):
        with self.rotkelchen.lock:
            balances = self.rotkelchen.query_bank_balances()
            return {
                'total': self.get_total_in_main_currency(balances)
            }

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

    def process_trade_history(self, start_ts, end_ts):
        start_ts = int(start_ts)
        end_ts = int(end_ts)
        with self.rotkelchen.lock:
            result = self.rotkelchen.process_history(start_ts, end_ts)

        print('process_trade_history() done')
        return process_result(result)

    def test(self, from_csv):
        if from_csv == "True":
            from_csv = True
        elif from_csv == "False":
            from_csv = False
        else:
            raise ValueError("Illegal value {} for argument from_csv".format(from_csv))

        start_ts = 1451606400  # 01/01/2016
        end_ts = 1483228799  # 31/12/2016
        with self.rotkelchen.lock:
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
        with self.rotkelchen.lock:
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
        with self.rotkelchen.lock:
            result = query_txlist("0xd1b8d347fd50dc7838a8ceb4294b6621b0b300f6", False)
        return result

    def test4(self):
        with self.rotkelchen.lock:
            result = self.rotkelchen.poloniex.returnLendingHistory()
        return result

    def test5(self):
        with self.rotkelchen.lock:
            result = self.rotkelchen.kraken.query_balances()
        return result

    def echo(self, text):
        return text

    def main(self):
        gevent.hub.signal(signal.SIGINT, self.shutdown)
        gevent.hub.signal(signal.SIGTERM, self.shutdown)
        self.zerorpc = zerorpc.Server(rotkelchen_server)
        addr = 'tcp://127.0.0.1:' + str(self.port())
        self.zerorpc.bind(addr)
        print('start running on {}'.format(addr))
        self.zerorpc.run()


if __name__ == '__main__':
    try:
        rotkelchen_server = RotkelchenServer()
    except:
        tb = traceback.format_exc()
        # open a file and dump the stack trace
        with open("error.log", "w") as f:
            f.write(tb)
        print("Failed to start rotkelchen backend:\n{}".format(tb))
        sys.exit(1)
    rotkelchen_server.main()
