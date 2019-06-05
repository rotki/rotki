import argparse
from collections import namedtuple
from unittest.mock import patch

import pytest

from rotkehlchen.rotkehlchen import Rotkehlchen
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


def initialize_mock_rotkehlchen_instance(
        rotki,
        start_with_logged_in_user,
        msg_aggregator,
        username,
        accountant,
        blockchain,
        db_password,
):
    if start_with_logged_in_user:
        # Rotkehlchen initializes its own messages aggregator normally but here we
        # should use the one all other fixtures use so that the same aggregator is
        # used across all objects in a test
        # TODO: Find a better way to achieve this
        rotki.msg_aggregator = msg_aggregator
        rotki.data.msg_aggregator = rotki.msg_aggregator
        # Unlock must come after we have set the aggregator if we are to get the
        # messages caused by DB initialization
        rotki.data.unlock(username, db_password, create_new=True)
        rotki.password = db_password
        # Remember accountant fixture has a mocked accounting data dir
        # different to the usual user one
        rotki.accountant = accountant
        rotki.blockchain = blockchain
        rotki.trades_historian = object()
        rotki.user_is_logged_in = True


@pytest.fixture()
def rotkehlchen_server(
        cli_args,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        function_scope_messages_aggregator,
        db_password,
):
    """A partially mocked rotkehlchen server instance"""
    with patch.object(argparse.ArgumentParser, 'parse_args', return_value=cli_args):
        server = RotkehlchenServer()

    initialize_mock_rotkehlchen_instance(
        rotki=server.rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        msg_aggregator=function_scope_messages_aggregator,
        username=username,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
    )
    return server


@pytest.fixture()
def rotkehlchen_instance(
        cli_args,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        function_scope_messages_aggregator,
        db_password,
):
    """A partially mocked rotkehlchen instance"""
    rotkehlchen = Rotkehlchen(cli_args)

    initialize_mock_rotkehlchen_instance(
        rotki=rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        msg_aggregator=function_scope_messages_aggregator,
        username=username,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
    )
    return rotkehlchen


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
