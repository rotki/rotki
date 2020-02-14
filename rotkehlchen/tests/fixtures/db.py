import os
from typing import Any, Dict, List, Optional

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import BlockchainAccounts
from rotkehlchen.tests.utils.constants import DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.typing import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    FilePath,
    SupportedBlockchain,
)
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


@pytest.fixture
def data_dir(tmpdir_factory) -> FilePath:
    return FilePath(tmpdir_factory.mktemp('data'))


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


def _init_database(
        data_dir: FilePath,
        password: str,
        msg_aggregator: MessagesAggregator,
        db_settings: Optional[Dict[str, Any]],
        ignored_assets: Optional[List[Asset]],
        blockchain_accounts: BlockchainAccounts,
        include_etherscan_key: bool,
) -> DBHandler:
    db = DBHandler(data_dir, password, msg_aggregator)
    settings = {
        # DO not submit usage analytics during tests
        'submit_usage_analytics': False,
        'main_currency': DEFAULT_TESTS_MAIN_CURRENCY,
    }
    # Set the given db_settings. The pre-set values have priority unless overriden here
    if db_settings is not None:
        for key, value in db_settings.items():
            settings[key] = value
    db.set_settings(ModifiableDBSettings(**settings))

    if ignored_assets:
        for asset in ignored_assets:
            db.add_to_ignored_assets(asset)

    # Make sure that the fixture provided accounts are in the blockchain
    db.add_blockchain_accounts(SupportedBlockchain.ETHEREUM, blockchain_accounts.eth)
    db.add_blockchain_accounts(SupportedBlockchain.BITCOIN, blockchain_accounts.btc)
    if include_etherscan_key:
        # Add the tests only etherscan API key
        db.add_external_service_credentials([ExternalServiceApiCredentials(
            service=ExternalService.ETHERSCAN,
            api_key=ApiKey('8JT7WQBB2VQP5C3416Y8X3S8GBA3CVZKP4'),
        )])

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
    )


@pytest.fixture
def db_settings() -> Optional[Dict[str, Any]]:
    return None


@pytest.fixture(scope='session')
def session_db_settings() -> Optional[Dict[str, Any]]:
    return None
