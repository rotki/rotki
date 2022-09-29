import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.data_migrations.migrations.migration_4 import read_and_write_nodes_in_database
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.tests.utils.database import (
    _use_prepared_db,
    add_blockchain_accounts_to_db,
    add_manually_tracked_balances_to_test_db,
    add_settings_to_test_db,
    add_tags_to_test_db,
    maybe_include_cryptocompare_key,
    maybe_include_etherscan_key,
)
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='username')
def fixture_username():
    return 'testuser'


@pytest.fixture(scope='session', name='session_ignored_assets')
def fixture_session_ignored_assets() -> Optional[List[Asset]]:
    return None


@pytest.fixture(name='ignored_assets')
def fixture_ignored_assets() -> Optional[List[Asset]]:
    return None


@pytest.fixture(scope='session', name='session_username')
def fixture_session_username():
    return 'session_test_user'


@pytest.fixture(scope='session', name='session_data_dir')
def fixture_session_data_dir(tmpdir_factory) -> Path:
    return Path(tmpdir_factory.mktemp('session_data'))


@pytest.fixture(name='user_data_dir')
def fixture_user_data_dir(data_dir, username) -> Path:
    """Create and return the user data directory"""
    user_data_dir = data_dir / username
    user_data_dir.mkdir(exist_ok=True)
    return user_data_dir


@pytest.fixture(scope='session', name='session_user_data_dir')
def fixture_session_user_data_dir(session_data_dir, session_username) -> Path:
    """Create and return the session scoped user data directory"""
    user_data_dir = session_data_dir / session_username
    user_data_dir.mkdir(exist_ok=True)
    return user_data_dir


@pytest.fixture(name='include_cryptocompare_key')
def fixture_include_cryptocompare_key() -> bool:
    """By default use a cryptocompare API key only in the OSX CI"""
    return 'CI' in os.environ and sys.platform == 'darwin'


@pytest.fixture(scope='session', name='session_include_cryptocompare_key')
def fixture_session_include_cryptocompare_key() -> bool:
    """By default use a cryptocompare API key only in the OSX CI"""
    return 'CI' in os.environ and sys.platform == 'darwin'


@pytest.fixture(name='include_etherscan_key')
def fixture_include_etherscan_key() -> bool:
    return True


@pytest.fixture(scope='session', name='session_include_etherscan_key')
def fixture_session_include_etherscan_key() -> bool:
    return True


@pytest.fixture(name='tags')
def fixture_tags() -> List[Dict[str, Any]]:
    return []


@pytest.fixture(scope='session', name='session_tags')
def fixture_session_tags() -> List[Dict[str, Any]]:
    return []


@pytest.fixture(name='manually_tracked_balances')
def fixture_manually_tracked_balances() -> List[ManuallyTrackedBalance]:
    return []


@pytest.fixture(scope='session', name='session_manually_tracked_balances')
def fixture_session_manually_tracked_balances() -> List[ManuallyTrackedBalance]:
    return []


@pytest.fixture(name='sql_vm_instructions_cb')
def fixture_sql_vm_instructions_cb() -> int:
    return DEFAULT_SQL_VM_INSTRUCTIONS_CB


@pytest.fixture(scope='session', name='session_sql_vm_instructions_cb')
def fixture_session_sql_vm_instructions_cb() -> int:
    return DEFAULT_SQL_VM_INSTRUCTIONS_CB


def _init_database(
        data_dir: Path,
        password: str,
        msg_aggregator: MessagesAggregator,
        db_settings: Optional[Dict[str, Any]],
        ignored_assets: Optional[List[Asset]],
        blockchain_accounts: BlockchainAccounts,
        include_etherscan_key: bool,
        include_cryptocompare_key: bool,
        tags: List[Dict[str, Any]],
        manually_tracked_balances: List[ManuallyTrackedBalance],
        data_migration_version: int,
        use_custom_database: Optional[str],
        sql_vm_instructions_cb: int,
) -> DBHandler:
    if use_custom_database is not None:
        _use_prepared_db(data_dir, use_custom_database)

    db = DBHandler(
        user_data_dir=data_dir,
        password=password,
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
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
        perform_nodes_insertion,
        sql_vm_instructions_cb,
) -> Optional[DBHandler]:
    if not start_with_logged_in_user:
        return None

    db_handler = _init_database(
        data_dir=user_data_dir,
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
    )
    if perform_nodes_insertion:
        with db_handler.user_write() as cursor:
            read_and_write_nodes_in_database(write_cursor=cursor)
    return db_handler


@pytest.fixture(scope='session')
def session_database(
        session_globaldb,  # pylint: disable=unused-argument  # needed for init_database
        session_user_data_dir,
        messages_aggregator,
        session_db_password,
        session_db_settings,
        session_start_with_logged_in_user,
        session_ignored_assets,
        session_include_etherscan_key,
        session_include_cryptocompare_key,
        session_tags,
        session_manually_tracked_balances,
        data_migration_version,
        session_use_custom_database,
        session_sql_vm_instructions_cb,
) -> Optional[DBHandler]:
    if not session_start_with_logged_in_user:
        return None

    # No sessions blockchain accounts given
    blockchain_accounts = BlockchainAccounts([], [], [], [], [], [])
    return _init_database(
        data_dir=session_user_data_dir,
        msg_aggregator=messages_aggregator,
        password=session_db_password,
        db_settings=session_db_settings,
        ignored_assets=session_ignored_assets,
        blockchain_accounts=blockchain_accounts,
        include_etherscan_key=session_include_etherscan_key,
        include_cryptocompare_key=session_include_cryptocompare_key,
        tags=session_tags,
        manually_tracked_balances=session_manually_tracked_balances,
        data_migration_version=data_migration_version,
        use_custom_database=session_use_custom_database,
        sql_vm_instructions_cb=session_sql_vm_instructions_cb,
    )


@pytest.fixture(name='db_settings')
def fixture_db_settings() -> Optional[Dict[str, Any]]:
    return None


@pytest.fixture(scope='session', name='session_db_settings')
def fixture_session_db_settings() -> Optional[Dict[str, Any]]:
    return None


@pytest.fixture(name='use_custom_database')
def fixture_use_custom_database() -> Optional[str]:
    return None


@pytest.fixture(scope='session', name='session_use_custom_database')
def fixture_session_use_custom_database() -> Optional[str]:
    return None
