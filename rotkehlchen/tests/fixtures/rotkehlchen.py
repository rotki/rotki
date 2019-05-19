import argparse
from collections import namedtuple
from unittest.mock import patch

import pytest

from rotkehlchen.server import RotkehlchenServer


@pytest.fixture
def start_with_logged_in_user():
    return True


@pytest.fixture()
def cli_args(data_dir):
    args = namedtuple('args', [
        'output',
        'sleep_secs',
        'notify',
        'data_dir',
        'zerorpc_port',
        'ethrpc_endpoint',
        'logfile',
        'logtarget',
        'loglevel',
        'logfromothermodules',
    ])
    args.loglevel = 'debug'
    args.logfromothermodules = False
    args.sleep_secs = 60
    args.data_dir = data_dir
    return args


@pytest.fixture()
def rotkehlchen_server(cli_args, username, blockchain, accountant, start_with_logged_in_user):
    """A partially mocked rotkehlchen server instance"""
    with patch.object(argparse.ArgumentParser, 'parse_args', return_value=cli_args):
        server = RotkehlchenServer()

    r = server.rotkehlchen
    if start_with_logged_in_user:
        r.data.unlock(username, '123', create_new=True)
        # Remember accountant fixture has a mocked accounting data dir
        # different to the usual user one
        r.accountant = accountant
        r.blockchain = blockchain
        r.trades_historian = object()
        r.user_is_logged_in = True
    return server
