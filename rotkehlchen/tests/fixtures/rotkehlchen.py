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
def rotkehlchen_server(
        cli_args,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        messages_aggregator,
):
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
        # Rotkehlchen initializes its own messages aggregator normally but here we
        # should use the one all other fixtures use so that the same aggregator is
        # used across all objects in a test
        r.msg_aggregator = messages_aggregator
    return server


@pytest.fixture()
def rotkehlchen_server_with_exchanges(
        rotkehlchen_server,
        function_scope_kraken,
        function_scope_poloniex,
        function_scope_bittrex,
        function_scope_binance,
):
    """Adds mock exchange objects to the rotkehlchen_server fixture"""
    rotkehlchen_server.rotkehlchen.kraken = function_scope_kraken
    rotkehlchen_server.rotkehlchen.poloniex = function_scope_poloniex
    rotkehlchen_server.rotkehlchen.bittrex = function_scope_bittrex
    rotkehlchen_server.rotkehlchen.binance = function_scope_binance
    return rotkehlchen_server
