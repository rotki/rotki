import base64
import contextlib
from contextlib import ExitStack
from typing import Optional
from unittest.mock import patch

import pytest

import rotkehlchen.tests.utils.exchanges as exchange_tests
from rotkehlchen.constants.misc import DEFAULT_MAX_LOG_SIZE_IN_MB
from rotkehlchen.data_migrations.manager import LAST_DATA_MIGRATION
from rotkehlchen.db.settings import DBSettings, ModifiableDBSettings
from rotkehlchen.exchanges.constants import EXCHANGES_WITH_PASSPHRASE
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.api import create_api_server
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    add_blockchain_accounts_to_db,
    add_manually_tracked_balances_to_test_db,
    add_settings_to_test_db,
    add_tags_to_test_db,
    maybe_include_cryptocompare_key,
    maybe_include_etherscan_key,
    mock_db_schema_sanity_check,
    perform_new_db_unlock_actions,
    run_no_db_upgrades,
)
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.tests.utils.evm import maybe_mock_evm_inquirer
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.history import maybe_mock_historical_price_queries
from rotkehlchen.tests.utils.inquirer import inquirer_inject_ethereum_set_order
from rotkehlchen.tests.utils.mock import mock_proxies, patch_avalanche_request
from rotkehlchen.tests.utils.substrate import wait_until_all_substrate_nodes_connected
from rotkehlchen.types import AVAILABLE_MODULES_MAP, Location


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


@pytest.fixture(name='data_migration_version', scope='session')
def fixture_data_migration_version() -> int:
    return LAST_DATA_MIGRATION


@pytest.fixture(name='max_size_in_mb_all_logs')
def fixture_max_size_in_mb_all_logs() -> int:
    return DEFAULT_MAX_LOG_SIZE_IN_MB


@pytest.fixture(name='cli_args')
def fixture_cli_args(data_dir, ethrpc_endpoint, max_size_in_mb_all_logs):
    return default_args(data_dir=data_dir, ethrpc_endpoint=ethrpc_endpoint, max_size_in_mb_all_logs=max_size_in_mb_all_logs)  # noqa: E501


@pytest.fixture(name='perform_upgrades_at_unlock')
def fixture_perform_upgrades_at_unlock():
    """Perform user DB upgrades as normal during user unlock"""
    return True


@pytest.fixture(name='add_accounts_to_db')
def fixture_add_blockchain_accounts_to_db():
    """If True, adds blockchain accounts to the db at unlock"""
    return True


@pytest.fixture(name='new_db_unlock_actions')
def fixture_new_db_unlock_actions():
    """Overwrite actions to perform at unlock of a fresh DB. None means overwrite with nothing.

    Otherwise it's a sequence of actions to overwrite it with. Valid actions are:
    ('rpc_nodes',)

    Default is just to write rpc nodes in the DB
    """
    return ('rpc_nodes',)


def patch_and_enter_before_unlock(
        rotki: Rotkehlchen,
        stack: contextlib.ExitStack,
        network_mocking: bool,
        ethereum_modules: list,
        ksm_rpc_endpoint: str,
        ethereum_manager_connect_at_start: list,
        optimism_manager_connect_at_start: list,
        kusama_manager_connect_at_start: list,
        have_decoders: bool,
        use_custom_database: bool,
        new_db_unlock_actions,
        perform_upgrades_at_unlock: bool,
        should_mock_settings: bool = True,
):
    # Do not connect to the usual nodes at start by default. Do not want to spam
    # them during our tests. It's configurable per test, with the default being nothing
    rpc_nodes_result = ethereum_manager_connect_at_start + optimism_manager_connect_at_start if network_mocking is False else []  # noqa: E501
    evm_rpcconnect_patch = patch(
        'rotkehlchen.db.dbhandler.DBHandler.get_rpc_nodes',
        return_value=rpc_nodes_result,
    )

    ksm_rpcconnect_patch = patch(
        'rotkehlchen.rotkehlchen.KUSAMA_NODES_TO_CONNECT_AT_START',
        new=kusama_manager_connect_at_start,
    )
    # patch the constants to make sure that the periodic query for icons
    # does not run during tests
    size_patch = patch('rotkehlchen.rotkehlchen.ICONS_BATCH_SIZE', new=0)
    sleep_patch = patch('rotkehlchen.rotkehlchen.ICONS_QUERY_SLEEP', new=999999)
    # don't perform checks for updates
    rotki_updates_patch = patch(
        'rotkehlchen.db.updates.RotkiDataUpdater.check_for_updates',
        autospec=True,
    )

    # And now enter all patched contexts
    stack.enter_context(evm_rpcconnect_patch)
    stack.enter_context(ksm_rpcconnect_patch)
    stack.enter_context(size_patch)
    stack.enter_context(sleep_patch)
    stack.enter_context(rotki_updates_patch)

    # Mock the initial get settings to include the specified ethereum modules
    if should_mock_settings:
        def mock_get_settings(_cursor) -> DBSettings:
            settings = DBSettings(
                active_modules=ethereum_modules,
                ksm_rpc_endpoint=ksm_rpc_endpoint,
            )
            return settings
        settings_patch = patch.object(rotki, 'get_settings', side_effect=mock_get_settings)
        stack.enter_context(settings_patch)

    if have_decoders is False:  # do not initialize the decoders at all -- saves time
        no_decoder_patch = patch('rotkehlchen.chain.evm.decoding.decoder.EVMTransactionDecoder.__init__', side_effect=lambda **kwargs: None)  # noqa: E501
        stack.enter_context(no_decoder_patch)

    if use_custom_database is not None:
        stack.enter_context(mock_db_schema_sanity_check())

    if new_db_unlock_actions is None:
        new_db_unlock_actions_patch = patch('rotkehlchen.rotkehlchen.Rotkehlchen._perform_new_db_actions', side_effect=lambda *args: None)  # noqa: E501
    else:
        def actions_after_unlock(self) -> None:
            perform_new_db_unlock_actions(db=self.data.db, new_db_unlock_actions=new_db_unlock_actions)  # noqa: E501

        new_db_unlock_actions_patch = patch('rotkehlchen.rotkehlchen.Rotkehlchen._perform_new_db_actions', side_effect=actions_after_unlock, autospec=True)  # noqa: E501
    stack.enter_context(new_db_unlock_actions_patch)
    # disable migrations at unlock for tests
    stack.enter_context(patch(
        'rotkehlchen.data_migrations.manager.DataMigrationManager.maybe_migrate_data',
        side_effect=lambda *args: None,
    ))
    if perform_upgrades_at_unlock is False:
        upgrades_patch = patch(
            'rotkehlchen.db.upgrade_manager.DBUpgradeManager.run_upgrades',
            side_effect=run_no_db_upgrades,
            autospec=True,
        )
        stack.enter_context(upgrades_patch)


def patch_no_op_unlock(
        rotki: Rotkehlchen,
        stack: contextlib.ExitStack,
        should_mock_settings: bool = True,
):
    patch_and_enter_before_unlock(
        rotki=rotki,
        stack=stack,
        network_mocking=True,
        ethereum_modules=[],
        ksm_rpc_endpoint='',
        ethereum_manager_connect_at_start=[],
        optimism_manager_connect_at_start=[],
        kusama_manager_connect_at_start=[],
        have_decoders=False,
        use_custom_database=False,
        new_db_unlock_actions=None,
        perform_upgrades_at_unlock=False,
        should_mock_settings=should_mock_settings,
    )


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
        optimism_manager_connect_at_start,
        kusama_manager_connect_at_start,
        ksm_rpc_endpoint,
        max_tasks_num,
        legacy_messages_via_websockets,
        data_migration_version,
        use_custom_database,
        user_data_dir,
        perform_upgrades_at_unlock,
        new_db_unlock_actions,
        current_price_oracles_order,
        network_mocking,
        have_decoders,
        add_accounts_to_db,
):
    if not start_with_logged_in_user:
        return

    original_unlock = rotki.data.unlock

    def augmented_unlock(
            username: str,
            password: str,
            create_new: bool,
            resume_from_backup: bool,
            initial_settings: Optional[ModifiableDBSettings] = None,
    ):
        """This is an augmented_unlock for the tests where after the original data.unlock
        happening in the start of rotkehlchen.unlock_user() we also add various fixture data
        to the DB so they can be picked up by the rest of the unlock function logic"""
        return_value = original_unlock(
            username=username,
            password=password,
            create_new=create_new,
            initial_settings=initial_settings,
            resume_from_backup=resume_from_backup,
        )
        add_settings_to_test_db(rotki.data.db, db_settings, ignored_assets, data_migration_version)
        maybe_include_etherscan_key(rotki.data.db, include_etherscan_key)
        maybe_include_cryptocompare_key(rotki.data.db, include_cryptocompare_key)
        if add_accounts_to_db is True:
            add_blockchain_accounts_to_db(rotki.data.db, blockchain_accounts)
        add_tags_to_test_db(rotki.data.db, tags)
        add_manually_tracked_balances_to_test_db(rotki.data.db, manually_tracked_balances)
        return return_value

    data_unlock_patch = patch.object(rotki.data, 'unlock', side_effect=augmented_unlock)

    create_new = True
    if use_custom_database is not None:
        _use_prepared_db(user_data_dir, use_custom_database)
        create_new = False

    with ExitStack() as stack:
        stack.enter_context(data_unlock_patch)
        patch_and_enter_before_unlock(
            rotki=rotki,
            stack=stack,
            network_mocking=network_mocking,
            ethereum_modules=ethereum_modules,
            ksm_rpc_endpoint=ksm_rpc_endpoint,
            ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
            optimism_manager_connect_at_start=optimism_manager_connect_at_start,
            kusama_manager_connect_at_start=kusama_manager_connect_at_start,
            have_decoders=have_decoders,
            use_custom_database=use_custom_database,
            new_db_unlock_actions=new_db_unlock_actions,
            perform_upgrades_at_unlock=perform_upgrades_at_unlock,
        )
        rotki.unlock_user(
            user=username,
            password=db_password,
            create_new=create_new,
            sync_approval='no',
            premium_credentials=None,
            resume_from_backup=False,
        )

    inquirer_inject_ethereum_set_order(
        inquirer=Inquirer(),
        add_defi_oracles=False,
        current_price_oracles_order=current_price_oracles_order,
        ethereum_manager=rotki.chains_aggregator.ethereum,
    )
    # configure when task manager should run for tests
    rotki.task_manager.max_tasks_num = max_tasks_num

    if start_with_valid_premium:
        rotki.premium = Premium(rotki_premium_credentials)
        rotki.premium_sync_manager.premium = rotki.premium
        rotki.chains_aggregator.premium = rotki.premium
        # Add premium to all the modules
        for module_name in AVAILABLE_MODULES_MAP:
            module = rotki.chains_aggregator.get_module(module_name)
            if module is not None:
                module.premium = rotki.premium

    if legacy_messages_via_websockets is False:
        rotki.msg_aggregator.rotki_notifier = None

    # After unlocking when all objects are created we need to also include
    # customized fixtures that may have been set by the tests
    rotki.chains_aggregator.accounts = blockchain_accounts

    maybe_mock_historical_price_queries(
        historian=PriceHistorian(),
        should_mock_price_queries=should_mock_price_queries,
        mocked_price_queries=mocked_price_queries,
        default_mock_value=default_mock_price_value,
    )
    if network_mocking is False:
        wait_until_all_nodes_connected(
            connect_at_start=ethereum_manager_connect_at_start,
            evm_inquirer=rotki.chains_aggregator.ethereum.node_inquirer,
        )
        wait_until_all_nodes_connected(
            connect_at_start=optimism_manager_connect_at_start,
            evm_inquirer=rotki.chains_aggregator.optimism.node_inquirer,
        )
    wait_until_all_substrate_nodes_connected(
        substrate_manager_connect_at_start=kusama_manager_connect_at_start,
        substrate_manager=rotki.chains_aggregator.kusama,
    )


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


@pytest.fixture(name='mocked_proxies')
def fixture_mocked_proxies():
    return None


@pytest.fixture(name='rotkehlchen_api_server')
def fixture_rotkehlchen_api_server(
        uninitialized_rotkehlchen,
        rest_api_port,
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
        optimism_manager_connect_at_start,
        kusama_manager_connect_at_start,
        ksm_rpc_endpoint,
        max_tasks_num,
        legacy_messages_via_websockets,
        data_migration_version,
        use_custom_database,
        user_data_dir,
        perform_upgrades_at_unlock,
        new_db_unlock_actions,
        current_price_oracles_order,
        network_mocking,
        mock_other_web3,
        ethereum_mock_data,
        optimism_mock_data,
        avalanche_mock_data,
        mocked_proxies,
        have_decoders,
        add_accounts_to_db,
):
    """A partially mocked rotkehlchen server instance"""

    api_server = create_api_server(
        rotki=uninitialized_rotkehlchen,
        rest_port_number=rest_api_port,
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
        optimism_manager_connect_at_start=optimism_manager_connect_at_start,
        kusama_manager_connect_at_start=kusama_manager_connect_at_start,
        ksm_rpc_endpoint=ksm_rpc_endpoint,
        max_tasks_num=max_tasks_num,
        legacy_messages_via_websockets=legacy_messages_via_websockets,
        data_migration_version=data_migration_version,
        use_custom_database=use_custom_database,
        user_data_dir=user_data_dir,
        perform_upgrades_at_unlock=perform_upgrades_at_unlock,
        new_db_unlock_actions=new_db_unlock_actions,
        current_price_oracles_order=current_price_oracles_order,
        network_mocking=network_mocking,
        have_decoders=have_decoders,
        add_accounts_to_db=add_accounts_to_db,
    )
    with ExitStack() as stack:
        if start_with_logged_in_user is True:
            if network_mocking is True:
                stack.enter_context(patch_avalanche_request(
                    api_server.rest_api.rotkehlchen.chains_aggregator.avalanche,
                    avalanche_mock_data,
                ))
                for evm_chain, connect_at_start, mock_data in (
                        ('ethereum', ethereum_manager_connect_at_start, ethereum_mock_data),
                        ('optimism', optimism_manager_connect_at_start, optimism_mock_data),
                        ('polygon_pos', [], {}),
                ):
                    maybe_mock_evm_inquirer(
                        should_mock=mock_other_web3,
                        parent_stack=stack,
                        evm_inquirer=getattr(api_server.rest_api.rotkehlchen.chains_aggregator, evm_chain).node_inquirer,  # noqa: E501
                        manager_connect_at_start=connect_at_start,
                        mock_data=mock_data,
                    )

            if mocked_proxies is not None:
                mock_proxies(stack, mocked_proxies)

            stack.enter_context(patch_decoder_reload_data())

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
        optimism_manager_connect_at_start,
        kusama_manager_connect_at_start,
        ksm_rpc_endpoint,
        max_tasks_num,
        legacy_messages_via_websockets,
        data_migration_version,
        use_custom_database,
        user_data_dir,
        perform_upgrades_at_unlock,
        new_db_unlock_actions,
        current_price_oracles_order,
        network_mocking,
        have_decoders,
        add_accounts_to_db,
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
        optimism_manager_connect_at_start=optimism_manager_connect_at_start,
        kusama_manager_connect_at_start=kusama_manager_connect_at_start,
        ksm_rpc_endpoint=ksm_rpc_endpoint,
        max_tasks_num=max_tasks_num,
        legacy_messages_via_websockets=legacy_messages_via_websockets,
        data_migration_version=data_migration_version,
        use_custom_database=use_custom_database,
        user_data_dir=user_data_dir,
        perform_upgrades_at_unlock=perform_upgrades_at_unlock,
        new_db_unlock_actions=new_db_unlock_actions,
        current_price_oracles_order=current_price_oracles_order,
        network_mocking=network_mocking,
        have_decoders=have_decoders,
        add_accounts_to_db=add_accounts_to_db,
    )
    return uninitialized_rotkehlchen


@pytest.fixture()
def rotkehlchen_api_server_with_exchanges(
        rotkehlchen_api_server,
        added_exchanges,
        gemini_test_base_uri,
        gemini_sandbox_api_secret,
        gemini_sandbox_api_key,
        okx_api_key,
        okx_api_secret,
        okx_passphrase,
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
        if exchange_location == Location.OKX:
            kwargs['api_key'] = okx_api_key
            kwargs['secret'] = okx_api_secret
            kwargs['passphrase'] = okx_passphrase
        if exchange_location == Location.BINANCEUS:
            kwargs['location'] = Location.BINANCEUS
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
