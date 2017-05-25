# Based on https://github.com/fyears/electron-python-example

from __future__ import print_function
import traceback
import sys
import gevent
import signal

import zerorpc

from args import app_args
from rotkelchen import Rotkelchen


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
