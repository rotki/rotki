import argparse
import base64
from collections import namedtuple
from unittest.mock import patch

import pytest

from rotkehlchen.data.importer import DataImporter
from rotkehlchen.history import TradesHistorian
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
        'sleep_secs',
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
        data_dir,
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
        rotki.data_importer = DataImporter(db=rotki.data.db)
        rotki.password = db_password
        # Remember accountant fixture has a mocked accounting data dir
        # different to the usual user one
        rotki.accountant = accountant
        rotki.blockchain = blockchain
        rotki.trades_historian = TradesHistorian(
            user_directory=data_dir,
            db=rotki.data.db,
            eth_accounts=rotki.data.get_eth_accounts(),
            msg_aggregator=rotki.msg_aggregator,
            exchange_manager=rotki.exchange_manager,
        )
        rotki.user_is_logged_in = True
        rotki.premium_sync_manager = PremiumSyncManager(
            data=rotki.data,
            password=db_password,
        )
        if start_with_valid_premium:
            rotki.premium = Premium(
                api_key=rotkehlchen_api_key,
                api_secret=rotkehlchen_api_secret,
            )
            rotki.premium_sync_manager.premium = rotki.premium
        else:
            rotki.premium = None

        # DO not submit usage analytics during tests


@pytest.fixture()
def uninitialized_rotkehlchen(cli_args):
    """A rotkehlchen instance that has only had __init__ run but is not unlocked"""
    return Rotkehlchen(cli_args)


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
        accounting_data_dir,
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
        data_dir=accounting_data_dir,
    )
    return server


@pytest.fixture()
def rotkehlchen_instance(
        uninitialized_rotkehlchen,
        username,
        blockchain,
        accountant,
        start_with_logged_in_user,
        start_with_valid_premium,
        function_scope_messages_aggregator,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
        accounting_data_dir,
):
    """A partially mocked rotkehlchen instance"""

    initialize_mock_rotkehlchen_instance(
        rotki=uninitialized_rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        msg_aggregator=function_scope_messages_aggregator,
        username=username,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
        rotkehlchen_api_key=rotkehlchen_api_key,
        rotkehlchen_api_secret=rotkehlchen_api_secret,
        data_dir=accounting_data_dir,
    )
    return uninitialized_rotkehlchen


@pytest.fixture()
def rotkehlchen_server_with_exchanges(
        rotkehlchen_server,
        function_scope_kraken,
        function_scope_poloniex,
        function_scope_bittrex,
        function_scope_binance,
        mock_bitmex,
):
    """Adds mock exchange objects to the rotkehlchen_server fixture"""
    exchanges = rotkehlchen_server.rotkehlchen.exchange_manager.connected_exchanges
    exchanges['kraken'] = function_scope_kraken
    exchanges['poloniex'] = function_scope_poloniex
    exchanges['bittrex'] = function_scope_bittrex
    exchanges['binance'] = function_scope_binance
    exchanges['bitmex'] = mock_bitmex
    return rotkehlchen_server
