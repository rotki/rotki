import argparse
import base64
from collections import namedtuple
from unittest.mock import patch

import pytest

from rotkehlchen.premium.premium import Premium
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.server import RotkehlchenServer
from rotkehlchen.tests.utils.factories import make_random_b64bytes


@pytest.fixture
def start_with_logged_in_user():
    return True


@pytest.fixture
def start_with_valid_premium():
    return False


@pytest.fixture
def rotkehlchen_api_key():
    return base64.b64encode(make_random_b64bytes(128))


@pytest.fixture
def rotkehlchen_api_secret():
    return base64.b64encode(make_random_b64bytes(128))


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
        start_with_valid_premium,
        msg_aggregator,
        username,
        accountant,
        blockchain,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
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
        if start_with_valid_premium:
            rotki.premium = Premium(
                api_key=rotkehlchen_api_key,
                api_secret=rotkehlchen_api_secret,
            )
            rotki.premium_sync_manager = PremiumSyncManager(
                data=rotki.data,
                password=db_password,
            )
            rotki.premium_sync_manager.premium = rotki.premium
        else:
            rotki.premium = None
            rotki.premium_sync_manager = None


@pytest.fixture()
def rotkehlchen_server(
        cli_args,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        start_with_valid_premium,
        function_scope_messages_aggregator,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    """A partially mocked rotkehlchen server instance"""
    with patch.object(argparse.ArgumentParser, 'parse_args', return_value=cli_args):
        server = RotkehlchenServer()

    initialize_mock_rotkehlchen_instance(
        rotki=server.rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        msg_aggregator=function_scope_messages_aggregator,
        username=username,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
        rotkehlchen_api_key=rotkehlchen_api_key,
        rotkehlchen_api_secret=rotkehlchen_api_secret,
    )
    return server


@pytest.fixture()
def rotkehlchen_instance(
        cli_args,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        start_with_valid_premium,
        function_scope_messages_aggregator,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    """A partially mocked rotkehlchen instance"""
    rotkehlchen = Rotkehlchen(cli_args)

    initialize_mock_rotkehlchen_instance(
        rotki=rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        msg_aggregator=function_scope_messages_aggregator,
        username=username,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
        rotkehlchen_api_key=rotkehlchen_api_key,
        rotkehlchen_api_secret=rotkehlchen_api_secret,
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
