import base64
from collections import namedtuple

import pytest

from rotkehlchen.data.importer import DataImporter
from rotkehlchen.history import TradesHistorian
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import create_api_server
from rotkehlchen.tests.utils.factories import make_random_b64bytes


@pytest.fixture
def start_with_logged_in_user():
    return True


@pytest.fixture(scope='session')
def session_start_with_logged_in_user():
    return True


@pytest.fixture
def start_with_valid_premium():
    return False


@pytest.fixture
def rotki_premium_credentials() -> PremiumCredentials:
    return PremiumCredentials(
        given_api_key=base64.b64encode(make_random_b64bytes(128)),
        given_api_secret=base64.b64encode(make_random_b64bytes(128)),
    )


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
        accountant,
        blockchain,
        db_password,
        rotki_premium_credentials,
        data_dir,
        database,
        username,
        etherscan,
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
        rotki.data.db = database
        rotki.data.username = username
        rotki.data.logged_in = True
        rotki.data_importer = DataImporter(db=rotki.data.db)
        rotki.password = db_password
        # Remember accountant fixture has a mocked accounting data dir
        # different to the usual user one. Accountant would normally be unlocked
        # during the normal unlock but due to mocking initialization has to be tweaked here
        rotki.accountant = accountant
        rotki.blockchain = blockchain
        rotki.trades_historian = TradesHistorian(
            user_directory=data_dir,
            db=rotki.data.db,
            msg_aggregator=rotki.msg_aggregator,
            exchange_manager=rotki.exchange_manager,
            etherscan=etherscan,
        )
        rotki.user_is_logged_in = True
        rotki.premium_sync_manager = PremiumSyncManager(
            data=rotki.data,
            password=db_password,
        )
        if start_with_valid_premium:
            rotki.premium = Premium(rotki_premium_credentials)
            rotki.premium_sync_manager.premium = rotki.premium
        else:
            rotki.premium = None


@pytest.fixture()
def uninitialized_rotkehlchen(cli_args):
    """A rotkehlchen instance that has only had __init__ run but is not unlocked"""
    return Rotkehlchen(cli_args)


@pytest.fixture()
def rotkehlchen_api_server(
        uninitialized_rotkehlchen,
        database,
        api_port,
        blockchain,
        accountant,
        start_with_logged_in_user,
        start_with_valid_premium,
        function_scope_messages_aggregator,
        db_password,
        rotki_premium_credentials,
        accounting_data_dir,
        username,
        etherscan,
):
    """A partially mocked rotkehlchen server instance"""

    api_server = create_api_server(rotki=uninitialized_rotkehlchen, port_number=api_port)

    initialize_mock_rotkehlchen_instance(
        rotki=api_server.rest_api.rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        msg_aggregator=function_scope_messages_aggregator,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
        rotki_premium_credentials=rotki_premium_credentials,
        data_dir=accounting_data_dir,
        database=database,
        username=username,
        etherscan=etherscan,
    )
    return api_server


@pytest.fixture()
def rotkehlchen_instance(
        uninitialized_rotkehlchen,
        database,
        blockchain,
        accountant,
        start_with_logged_in_user,
        start_with_valid_premium,
        function_scope_messages_aggregator,
        db_password,
        rotki_premium_credentials,
        accounting_data_dir,
        username,
        etherscan,
):
    """A partially mocked rotkehlchen instance"""

    initialize_mock_rotkehlchen_instance(
        rotki=uninitialized_rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        msg_aggregator=function_scope_messages_aggregator,
        accountant=accountant,
        blockchain=blockchain,
        db_password=db_password,
        rotki_premium_credentials=rotki_premium_credentials,
        data_dir=accounting_data_dir,
        database=database,
        username=username,
        etherscan=etherscan,
    )
    return uninitialized_rotkehlchen


@pytest.fixture()
def rotkehlchen_api_server_with_exchanges(
        rotkehlchen_api_server,
        added_exchanges,
        function_scope_kraken,
        function_scope_poloniex,
        function_scope_bittrex,
        function_scope_binance,
        mock_bitmex,
):
    """Adds mock exchange objects to the rotkehlchen_server fixture"""
    exchanges = rotkehlchen_api_server.rest_api.rotkehlchen.exchange_manager.connected_exchanges
    if 'kraken' in added_exchanges:
        exchanges['kraken'] = function_scope_kraken
    if 'poloniex' in added_exchanges:
        exchanges['poloniex'] = function_scope_poloniex
    if 'bittrex' in added_exchanges:
        exchanges['bittrex'] = function_scope_bittrex
    if 'binance' in added_exchanges:
        exchanges['binance'] = function_scope_binance
    if 'bitmex' in added_exchanges:
        exchanges['bitmex'] = mock_bitmex

    # TODO: Also add coinbase and coinbasepro here and in the history tests and utils

    return rotkehlchen_api_server
