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
        print("Failed to start rotkelchen backend")
        sys.exit(1)
    rotkelchen_server.main()
