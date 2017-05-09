# Based on https://github.com/fyears/electron-python-example

from __future__ import print_function
import zerorpc

from args import app_args
from rotkelchen import Rotkelchen


def parse_port():
    return 4242


def main():
    addr = 'tcp://127.0.0.1:' + str(parse_port())
    args = app_args()
    rotkelchen = Rotkelchen(args)
    s = zerorpc.Server(rotkelchen)
    s.bind(addr)
    print('start running on {}'.format(addr))
    s.run()

if __name__ == '__main__':
    main()
