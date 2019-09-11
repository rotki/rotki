import os

import pytest

from rotkehlchen.db.dbhandler import DBHandler


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


@pytest.fixture
def database(user_data_dir, function_scope_messages_aggregator):
    return DBHandler(user_data_dir, '123', function_scope_messages_aggregator)


@pytest.fixture(scope='session')
def session_database(session_user_data_dir, messages_aggregator):
    return DBHandler(session_user_data_dir, '123', messages_aggregator)
