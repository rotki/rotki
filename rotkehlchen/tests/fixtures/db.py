import os
from typing import Any, Dict, List, Optional

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.tests.utils.database import (
    add_blockchain_accounts_to_db,
    add_manually_tracked_balances_to_test_db,
    add_settings_to_test_db,
    add_tags_to_test_db,
    maybe_include_etherscan_key,
)
from rotkehlchen.typing import FilePath
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def username():
    return 'testuser'


@pytest.fixture(scope='session')
def session_ignored_assets() -> Optional[List[Asset]]:
    return None


@pytest.fixture
def ignored_assets() -> Optional[List[Asset]]:
    return None


@pytest.fixture(scope='session')
def session_username():
    return 'session_test_user'


@pytest.fixture(scope='session')
def session_data_dir(tmpdir_factory) -> FilePath:
    return FilePath(tmpdir_factory.mktemp('session_data'))


@pytest.fixture
def user_data_dir(data_dir, username) -> FilePath:
    """Create and return the user data directory"""
    user_data_dir = os.path.join(data_dir, username)
    if not os.path.exists(user_data_dir):
        os.mkdir(user_data_dir)
    return FilePath(user_data_dir)


@pytest.fixture(scope='session')
def session_user_data_dir(session_data_dir, session_username):
    """Create and return the session scoped user data directory"""
    user_data_dir = os.path.join(session_data_dir, session_username)
    if not os.path.exists(user_data_dir):
        os.mkdir(user_data_dir)
    return user_data_dir


@pytest.fixture
def include_etherscan_key() -> bool:
    return True


@pytest.fixture(scope='session')
def session_include_etherscan_key() -> bool:
    return True


@pytest.fixture
def tags() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def session_tags() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def manually_tracked_balances() -> List[ManuallyTrackedBalance]:
    return []


@pytest.fixture
def session_manually_tracked_balances() -> List[ManuallyTrackedBalance]:
    return []


def _init_database(
        data_dir: FilePath,
        password: str,
        msg_aggregator: MessagesAggregator,
        db_settings: Optional[Dict[str, Any]],
        ignored_assets: Optional[List[Asset]],
        blockchain_accounts: BlockchainAccounts,
        include_etherscan_key: bool,
        tags: List[Dict[str, Any]],
        manually_tracked_balances: List[ManuallyTrackedBalance],
) -> DBHandler:
    db = DBHandler(data_dir, password, msg_aggregator)
    # Make sure that the fixture provided data are included in the DB
    add_settings_to_test_db(db, db_settings, ignored_assets)
    add_blockchain_accounts_to_db(db, blockchain_accounts)
    maybe_include_etherscan_key(db, include_etherscan_key)
    add_tags_to_test_db(db, tags)
    add_manually_tracked_balances_to_test_db(db, manually_tracked_balances)

    return db


@pytest.fixture
def database(
        user_data_dir,
        function_scope_messages_aggregator,
        db_password,
        db_settings,
        start_with_logged_in_user,
        ignored_assets,
        blockchain_accounts,
        include_etherscan_key,
        tags,
        manually_tracked_balances,
) -> Optional[DBHandler]:
    if not start_with_logged_in_user:
        return None

    return _init_database(
        data_dir=user_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        password=db_password,
        db_settings=db_settings,
        ignored_assets=ignored_assets,
        blockchain_accounts=blockchain_accounts,
        include_etherscan_key=include_etherscan_key,
        tags=tags,
        manually_tracked_balances=manually_tracked_balances,
    )


@pytest.fixture(scope='session')
def session_database(
        session_user_data_dir,
        messages_aggregator,
        session_db_password,
        session_db_settings,
        session_start_with_logged_in_user,
        session_ignored_assets,
        session_include_etherscan_key,
        session_tags,
        session_manually_tracked_balances,
) -> Optional[DBHandler]:
    if not session_start_with_logged_in_user:
        return None

    # No sessions blockchain accounts given
    blockchain_accounts = BlockchainAccounts([], [])
    return _init_database(
        data_dir=session_user_data_dir,
        msg_aggregator=messages_aggregator,
        password=session_db_password,
        db_settings=session_db_settings,
        ignored_assets=session_ignored_assets,
        blockchain_accounts=blockchain_accounts,
        include_etherscan_key=session_include_etherscan_key,
        tags=session_tags,
        manually_tracked_balances=session_manually_tracked_balances,
    )


@pytest.fixture
def db_settings() -> Optional[Dict[str, Any]]:
    return None


@pytest.fixture(scope='session')
def session_db_settings() -> Optional[Dict[str, Any]]:
    return None
