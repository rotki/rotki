import os
import sys
from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from shutil import rmtree
from typing import Any
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import BlockchainAccounts
from rotkehlchen.constants.misc import (
    DEFAULT_DB_POOL_SIZE,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    USERSDIR_NAME,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    add_blockchain_accounts_to_db,
    add_manually_tracked_balances_to_test_db,
    add_settings_to_test_db,
    add_tags_to_test_db,
    maybe_include_cryptocompare_key,
    maybe_include_etherscan_key,
    mock_db_schema_sanity_check,
    mock_dbhandler_sync_globaldb_assets,
    perform_new_db_unlock_actions,
    run_no_db_upgrades,
)
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='username')
def fixture_username():
    return 'testuser'


@pytest.fixture(name='ignored_assets')
def fixture_ignored_assets() -> list[Asset] | None:
    return None


@pytest.fixture(name='user_data_dir')
def fixture_user_data_dir(data_dir, username) -> Path:
    """Create and return the user data directory. Clean up old directory if existing"""
    user_data_dir = data_dir / USERSDIR_NAME / username
    rmtree(user_data_dir, ignore_errors=True)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return user_data_dir


@pytest.fixture(name='include_cryptocompare_key')
def fixture_include_cryptocompare_key() -> bool:
    """By default use a cryptocompare API key only in the OSX CI"""
    return 'CI' in os.environ and sys.platform == 'darwin'


@pytest.fixture(name='include_etherscan_key')
def fixture_include_etherscan_key() -> bool:
    return True


@pytest.fixture(name='tags')
def fixture_tags() -> list[dict[str, Any]]:
    return []


@pytest.fixture(name='manually_tracked_balances')
def fixture_manually_tracked_balances() -> list[ManuallyTrackedBalance]:
    return []


@pytest.fixture(name='sql_vm_instructions_cb')
def fixture_sql_vm_instructions_cb() -> int:
    return DEFAULT_SQL_VM_INSTRUCTIONS_CB


@pytest.fixture(name='db_pool_size')
def fixture_db_pool_size() -> int:
    return DEFAULT_DB_POOL_SIZE


def _init_database(
        user_data_dir: Path,
        password: str,
        msg_aggregator: MessagesAggregator,
        db_settings: dict[str, Any] | None,
        ignored_assets: list[Asset] | None,
        blockchain_accounts: BlockchainAccounts,
        include_etherscan_key: bool,
        include_cryptocompare_key: bool,
        tags: list[dict[str, Any]],
        manually_tracked_balances: list[ManuallyTrackedBalance],
        data_migration_version: int,
        use_custom_database: str | None,
        sql_vm_instructions_cb: int,
        db_pool_size: int,
        perform_upgrades_at_unlock: bool,
        skip_sync_globaldb_assets: bool,
) -> DBHandler:
    if use_custom_database is not None:
        _use_prepared_db(user_data_dir, use_custom_database)

    with ExitStack() as stack:
        if use_custom_database is not None:
            stack.enter_context(mock_db_schema_sanity_check())
        if perform_upgrades_at_unlock is False:
            upgrades_patch = patch(
                'rotkehlchen.db.upgrade_manager.DBUpgradeManager.run_upgrades',
                side_effect=run_no_db_upgrades,
                autospec=True,
            )
            stack.enter_context(upgrades_patch)
        if skip_sync_globaldb_assets:
            stack.enter_context(mock_dbhandler_sync_globaldb_assets())
        db = DBHandler(
            user_data_dir=user_data_dir,
            password=password,
            msg_aggregator=msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=sql_vm_instructions_cb,
            resume_from_backup=False,
            db_pool_size=db_pool_size,
        )
    # Make sure that the fixture provided data are included in the DB
    add_settings_to_test_db(db, db_settings, ignored_assets, data_migration_version)
    add_blockchain_accounts_to_db(db, blockchain_accounts)
    maybe_include_etherscan_key(db, include_etherscan_key)
    maybe_include_cryptocompare_key(db, include_cryptocompare_key)
    add_tags_to_test_db(db, tags)
    add_manually_tracked_balances_to_test_db(db, manually_tracked_balances)

    return db


@pytest.fixture
def database(
        globaldb,  # pylint: disable=unused-argument  # needed for init_database
        user_data_dir,
        function_scope_messages_aggregator,
        db_password,
        db_settings,
        start_with_logged_in_user,
        ignored_assets,
        blockchain_accounts,
        include_etherscan_key,
        include_cryptocompare_key,
        tags,
        manually_tracked_balances,
        data_migration_version,
        use_custom_database,
        new_db_unlock_actions,
        sql_vm_instructions_cb,
        db_pool_size,
        perform_upgrades_at_unlock,
        skip_sync_globaldb_assets,
) -> Generator[DBHandler | None, None, None]:
    if not start_with_logged_in_user:
        yield None
    else:
        db_handler = _init_database(
            user_data_dir=user_data_dir,
            msg_aggregator=function_scope_messages_aggregator,
            password=db_password,
            db_settings=db_settings,
            ignored_assets=ignored_assets,
            blockchain_accounts=blockchain_accounts,
            include_etherscan_key=include_etherscan_key,
            include_cryptocompare_key=include_cryptocompare_key,
            tags=tags,
            manually_tracked_balances=manually_tracked_balances,
            data_migration_version=data_migration_version,
            use_custom_database=use_custom_database,
            sql_vm_instructions_cb=sql_vm_instructions_cb,
            db_pool_size=db_pool_size,
            perform_upgrades_at_unlock=perform_upgrades_at_unlock,
            skip_sync_globaldb_assets=skip_sync_globaldb_assets,
        )
        if new_db_unlock_actions is not None:
            perform_new_db_unlock_actions(db=db_handler, new_db_unlock_actions=new_db_unlock_actions)  # noqa: E501
        yield db_handler

        db_handler.logout()


@pytest.fixture(name='db_settings')
def fixture_db_settings() -> dict[str, Any] | None:
    return None


@pytest.fixture(name='use_custom_database')
def fixture_use_custom_database() -> str | None:
    return None
