import base64
from collections import namedtuple
from unittest.mock import patch

import pytest

import rotkehlchen.tests.utils.exchanges as exchange_tests
from rotkehlchen.args import DEFAULT_MAX_LOG_BACKUP_FILES, DEFAULT_MAX_LOG_SIZE_IN_MB
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.exchanges.manager import EXCHANGES_WITH_PASSPHRASE
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import create_api_server
from rotkehlchen.tests.utils.database import (
    add_blockchain_accounts_to_db,
    add_manually_tracked_balances_to_test_db,
    add_settings_to_test_db,
    add_tags_to_test_db,
    maybe_include_cryptocompare_key,
    maybe_include_etherscan_key,
)
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.history import maybe_mock_historical_price_queries
from rotkehlchen.tests.utils.substrate import wait_until_all_substrate_nodes_connected
from rotkehlchen.typing import Location


@pytest.fixture(name='max_tasks_num')
def fixture_max_tasks_num() -> int:
    """The max number of tasks below which the manager can schedule tasks

    By default -1 which disables the task manager
    """
    return -1


@pytest.fixture(name='start_with_logged_in_user')
def fixture_start_with_logged_in_user():
    return True


@pytest.fixture(scope='session', name='session_start_with_logged_in_user')
def fixture_session_start_with_logged_in_user():
    return True


@pytest.fixture(name='start_with_valid_premium')
def fixture_start_with_valid_premium():
    return False


@pytest.fixture(name='legacy_messages_via_websockets')
def fixture_legacy_messages_via_websockets():
    """Decide whether rotki notifier will be instantiated for message aggregator in tests"""
    return False


@pytest.fixture(name='rotki_premium_credentials')
def fixture_rotki_premium_credentials() -> PremiumCredentials:
    return PremiumCredentials(
        given_api_key=base64.b64encode(make_random_b64bytes(128)).decode(),
        given_api_secret=base64.b64encode(make_random_b64bytes(128)).decode(),
    )


@pytest.fixture(name='cli_args')
def fixture_cli_args(data_dir, ethrpc_endpoint):
    args = namedtuple('args', [
        'sleep_secs',
        'data_dir',
        'zerorpc_port',
        'ethrpc_endpoint',
        'logfile',
        'logtarget',
        'loglevel',
        'logfromothermodules',
        'max_size_in_mb_all_logs',
        'max_logfiles_num',
    ])
    args.loglevel = 'debug'
    args.logfromothermodules = False
    args.sleep_secs = 60
    args.data_dir = data_dir
    args.ethrpc_endpoint = ethrpc_endpoint
    args.max_size_in_mb_all_logs = DEFAULT_MAX_LOG_SIZE_IN_MB
    args.max_logfiles_num = DEFAULT_MAX_LOG_BACKUP_FILES
    return args


def initialize_mock_rotkehlchen_instance(
        rotki,
        start_with_logged_in_user,
        start_with_valid_premium,
        db_password,
        rotki_premium_credentials,
        username,
        blockchain_accounts,
        include_etherscan_key,
        include_cryptocompare_key,
        should_mock_price_queries,
        mocked_price_queries,
        ethereum_modules,
        db_settings,
        ignored_assets,
        tags,
        manually_tracked_balances,
        default_mock_price_value,
        ethereum_manager_connect_at_start,
        kusama_manager_connect_at_start,
        eth_rpc_endpoint,
        ksm_rpc_endpoint,
        aave_use_graph,
        max_tasks_num,
        legacy_messages_via_websockets,
):
    if not start_with_logged_in_user:
        return

    # Mock the initial get settings to include the specified ethereum modules
    def mock_get_settings() -> DBSettings:
        settings = DBSettings(
            active_modules=ethereum_modules,
            eth_rpc_endpoint=eth_rpc_endpoint,
            ksm_rpc_endpoint=ksm_rpc_endpoint,
        )
        return settings
    settings_patch = patch.object(rotki, 'get_settings', side_effect=mock_get_settings)

    # Do not connect to the usual nodes at start by default. Do not want to spam
    # them during our tests. It's configurable per test, with the default being nothing
    eth_rpcconnect_patch = patch(
        'rotkehlchen.rotkehlchen.ETHEREUM_NODES_TO_CONNECT_AT_START',
        new=ethereum_manager_connect_at_start,
    )
    ksm_rpcconnect_patch = patch(
        'rotkehlchen.rotkehlchen.KUSAMA_NODES_TO_CONNECT_AT_START',
        new=kusama_manager_connect_at_start,
    )
    ksm_connect_on_startup_patch = patch.object(
        rotki,
        '_connect_ksm_manager_on_startup',
        return_value=bool(blockchain_accounts.ksm),
    )
    # patch the constants to make sure that the periodic query for icons
    # does not run during tests
    size_patch = patch('rotkehlchen.rotkehlchen.ICONS_BATCH_SIZE', new=0)
    sleep_patch = patch('rotkehlchen.rotkehlchen.ICONS_QUERY_SLEEP', new=999999)
    with settings_patch, eth_rpcconnect_patch, ksm_rpcconnect_patch, ksm_connect_on_startup_patch, size_patch, sleep_patch:  # noqa: E501
        rotki.unlock_user(
            user=username,
            password=db_password,
            create_new=True,
            sync_approval='no',
            premium_credentials=None,
        )
    # configure when task manager should run for tests
    rotki.task_manager.max_tasks_num = max_tasks_num

    if start_with_valid_premium:
        rotki.premium = Premium(rotki_premium_credentials)
        rotki.premium_sync_manager.premium = rotki.premium

    if legacy_messages_via_websockets is False:
        rotki.msg_aggregator.rotki_notifier = None

    # After unlocking when all objects are created we need to also include
    # customized fixtures that may have been set by the tests
    rotki.chain_manager.accounts = blockchain_accounts
    add_settings_to_test_db(rotki.data.db, db_settings, ignored_assets)
    maybe_include_etherscan_key(rotki.data.db, include_etherscan_key)
    maybe_include_cryptocompare_key(rotki.data.db, include_cryptocompare_key)
    add_blockchain_accounts_to_db(rotki.data.db, blockchain_accounts)
    add_tags_to_test_db(rotki.data.db, tags)
    add_manually_tracked_balances_to_test_db(rotki.data.db, manually_tracked_balances)
    maybe_mock_historical_price_queries(
        historian=PriceHistorian(),
        should_mock_price_queries=should_mock_price_queries,
        mocked_price_queries=mocked_price_queries,
        default_mock_value=default_mock_price_value,
    )
    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=rotki.chain_manager.ethereum,
    )
    wait_until_all_substrate_nodes_connected(
        substrate_manager_connect_at_start=kusama_manager_connect_at_start,
        substrate_manager=rotki.chain_manager.kusama,
    )

    aave = rotki.chain_manager.get_module('aave')
    if aave:
        aave.use_graph = aave_use_graph


@pytest.fixture(name='uninitialized_rotkehlchen')
def fixture_uninitialized_rotkehlchen(cli_args, inquirer, asset_resolver, globaldb):  # pylint: disable=unused-argument  # noqa: E501
    """A rotkehlchen instance that has only had __init__ run but is not unlocked

    Adding the inquirer fixture as a requirement to make sure that any mocking that
    happens at the inquirer level is reflected in the tests.

    For this to happen inquirer fixture must be initialized before Rotkehlchen so
    that the inquirer initialization in Rotkehlchen's __init__ uses the fixture's instance

    Adding the AssetResolver as a requirement so that the first initialization happens here
    """
    rotki = Rotkehlchen(cli_args)
    return rotki


@pytest.fixture(name='rotkehlchen_api_server')
def fixture_rotkehlchen_api_server(
        uninitialized_rotkehlchen,
        rest_api_port,
        websockets_api_port,
        start_with_logged_in_user,
        start_with_valid_premium,
        db_password,
        rotki_premium_credentials,
        username,
        blockchain_accounts,
        include_etherscan_key,
        include_cryptocompare_key,
        should_mock_price_queries,
        mocked_price_queries,
        ethereum_modules,
        db_settings,
        ignored_assets,
        tags,
        manually_tracked_balances,
        default_mock_price_value,
        ethereum_manager_connect_at_start,
        kusama_manager_connect_at_start,
        ethrpc_endpoint,
        ksm_rpc_endpoint,
        aave_use_graph,
        max_tasks_num,
        legacy_messages_via_websockets,
):
    """A partially mocked rotkehlchen server instance"""

    api_server = create_api_server(
        rotki=uninitialized_rotkehlchen,
        rest_port_number=rest_api_port,
        websockets_port_number=websockets_api_port,
    )

    initialize_mock_rotkehlchen_instance(
        rotki=api_server.rest_api.rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        db_password=db_password,
        rotki_premium_credentials=rotki_premium_credentials,
        username=username,
        blockchain_accounts=blockchain_accounts,
        include_etherscan_key=include_etherscan_key,
        include_cryptocompare_key=include_cryptocompare_key,
        should_mock_price_queries=should_mock_price_queries,
        mocked_price_queries=mocked_price_queries,
        ethereum_modules=ethereum_modules,
        db_settings=db_settings,
        ignored_assets=ignored_assets,
        tags=tags,
        manually_tracked_balances=manually_tracked_balances,
        default_mock_price_value=default_mock_price_value,
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        kusama_manager_connect_at_start=kusama_manager_connect_at_start,
        eth_rpc_endpoint=ethrpc_endpoint,
        ksm_rpc_endpoint=ksm_rpc_endpoint,
        aave_use_graph=aave_use_graph,
        max_tasks_num=max_tasks_num,
        legacy_messages_via_websockets=legacy_messages_via_websockets,
    )
    yield api_server
    api_server.stop()


@pytest.fixture()
def rotkehlchen_instance(
        uninitialized_rotkehlchen,
        start_with_logged_in_user,
        start_with_valid_premium,
        db_password,
        rotki_premium_credentials,
        username,
        blockchain_accounts,
        include_etherscan_key,
        include_cryptocompare_key,
        should_mock_price_queries,
        mocked_price_queries,
        ethereum_modules,
        db_settings,
        ignored_assets,
        tags,
        manually_tracked_balances,
        default_mock_price_value,
        ethereum_manager_connect_at_start,
        kusama_manager_connect_at_start,
        ethrpc_endpoint,
        ksm_rpc_endpoint,
        aave_use_graph,
        max_tasks_num,
        legacy_messages_via_websockets,
):
    """A partially mocked rotkehlchen instance"""

    initialize_mock_rotkehlchen_instance(
        rotki=uninitialized_rotkehlchen,
        start_with_logged_in_user=start_with_logged_in_user,
        start_with_valid_premium=start_with_valid_premium,
        db_password=db_password,
        rotki_premium_credentials=rotki_premium_credentials,
        username=username,
        blockchain_accounts=blockchain_accounts,
        include_etherscan_key=include_etherscan_key,
        include_cryptocompare_key=include_cryptocompare_key,
        should_mock_price_queries=should_mock_price_queries,
        mocked_price_queries=mocked_price_queries,
        ethereum_modules=ethereum_modules,
        db_settings=db_settings,
        ignored_assets=ignored_assets,
        tags=tags,
        manually_tracked_balances=manually_tracked_balances,
        default_mock_price_value=default_mock_price_value,
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        kusama_manager_connect_at_start=kusama_manager_connect_at_start,
        eth_rpc_endpoint=ethrpc_endpoint,
        ksm_rpc_endpoint=ksm_rpc_endpoint,
        aave_use_graph=aave_use_graph,
        max_tasks_num=max_tasks_num,
        legacy_messages_via_websockets=legacy_messages_via_websockets,
    )
    return uninitialized_rotkehlchen


@pytest.fixture()
def rotkehlchen_api_server_with_exchanges(
        rotkehlchen_api_server,
        added_exchanges,
        gemini_test_base_uri,
        gemini_sandbox_api_secret,
        gemini_sandbox_api_key,
):
    """Adds mock exchange objects to the rotkehlchen_server fixture"""
    exchanges = rotkehlchen_api_server.rest_api.rotkehlchen.exchange_manager.connected_exchanges
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    for exchange_location in added_exchanges:
        name = str(exchange_location)
        if exchange_location == Location.BINANCEUS:
            name = 'binance'
        create_fn = getattr(exchange_tests, f'create_test_{name}')
        passphrase = None
        kwargs = {}
        if exchange_location in EXCHANGES_WITH_PASSPHRASE:
            passphrase = '123'
            kwargs['passphrase'] = passphrase
        if exchange_location == Location.GEMINI:
            kwargs['base_uri'] = gemini_test_base_uri
            kwargs['api_key'] = gemini_sandbox_api_key
            kwargs['api_secret'] = gemini_sandbox_api_secret
        exchangeobj = create_fn(
            database=rotki.data.db,
            msg_aggregator=rotki.msg_aggregator,
            **kwargs,
        )
        kraken_account_type = exchangeobj.account_type if exchange_location == Location.KRAKEN else None  # noqa: E501
        exchanges[exchange_location] = [exchangeobj]
        # also add credentials in the DB
        rotki.data.db.add_exchange(
            name=exchangeobj.name,
            location=exchange_location,
            api_key=exchangeobj.api_key,
            api_secret=exchangeobj.secret,
            passphrase=passphrase,
            kraken_account_type=kraken_account_type,
        )

    yield rotkehlchen_api_server
    rotkehlchen_api_server.stop()
