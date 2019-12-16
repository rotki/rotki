import os
from typing import Any, Dict, Optional

import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def username():
    return 'testuser'


@pytest.fixture(scope='session')
def session_username():
    return 'session_test_user'


@pytest.fixture
def data_dir(tmpdir_factory):
    return tmpdir_factory.mktemp('data')


@pytest.fixture(scope='session')
def session_data_dir(tmpdir_factory):
    return tmpdir_factory.mktemp('session_data')


@pytest.fixture
def user_data_dir(data_dir, username):
    """Create and return the user data directory"""
    user_data_dir = os.path.join(data_dir, username)
    if not os.path.exists(user_data_dir):
        os.mkdir(user_data_dir)
    return user_data_dir


@pytest.fixture(scope='session')
def session_user_data_dir(session_data_dir, session_username):
    """Create and return the session scoped user data directory"""
    user_data_dir = os.path.join(session_data_dir, session_username)
    if not os.path.exists(user_data_dir):
        os.mkdir(user_data_dir)
    return user_data_dir


def _init_database(
        data_dir: str,
        password: str,
        msg_aggregator: MessagesAggregator,
        db_settings: Optional[Dict[str, Any]],
) -> DBHandler:
    db = DBHandler(data_dir, password, msg_aggregator)
    settings = {
        # DO not submit usage analytics during tests
        'submit_usage_analytics': False,
        # Default main currency for tests is EUR
        'main_currency': 'EUR',
    }
    # Set the given db_settings. But the pre-set values have priority
    if db_settings is not None:
        for key, value in db_settings.items():
            settings[key] = value

    db.set_settings(settings)
    return db


@pytest.fixture
def database(
        user_data_dir,
        function_scope_messages_aggregator,
        db_password,
        db_settings,
        start_with_logged_in_user,
) -> Optional[DBHandler]:
    if not start_with_logged_in_user:
        return None

    return _init_database(
        data_dir=user_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        password=db_password,
        db_settings=db_settings,
    )


@pytest.fixture(scope='session')
def session_database(
        session_user_data_dir,
        messages_aggregator,
        db_password,
        db_settings,
        start_with_logged_in_user,
) -> Optional[DBHandler]:
    if not start_with_logged_in_user:
        return None

    return _init_database(
        data_dir=session_user_data_dir,
        msg_aggregator=messages_aggregator,
        password=db_password,
        db_settings=db_settings,
    )


@pytest.fixture
def db_settings() -> Optional[Dict[str, Any]]:
    return None
