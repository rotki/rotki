import pytest
from collections import namedtuple

from rotkehlchen.rotkehlchen import Rotkehlchen


@pytest.fixture()
def cli_args(data_dir):
    args = namedtuple('args', [
        'output',
        'sleep_secs',
        'notify',
        'data_dir',
        'zerorpc_port',
        'ethrpc_port',
        'logfile',
        'logtarget',
        'loglevel',
        'logfromothermodules'
    ])
    args.loglevel = 'debug'
    args.logfromothermodules = False
    args.sleep_secs = 60
    args.data_dir = data_dir
    return args


@pytest.fixture()
def rotkehlchen_instance(cli_args, username, blockchain):
    r = Rotkehlchen(cli_args)
    r.data.unlock(username, '123', create_new=True)
    r.blockchain = blockchain
    return r
