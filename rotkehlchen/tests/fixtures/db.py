import os

import pytest

from rotkehlchen.db.dbhandler import DBHandler


@pytest.fixture
def username():
    return 'testuser'


@pytest.fixture
def data_dir(tmpdir_factory):
    return tmpdir_factory.mktemp('data')


@pytest.fixture(scope='session')
def session_data_dir(tmpdir_factory):
    return tmpdir_factory.mktemp('data')


@pytest.fixture
def user_data_dir(data_dir, username):
    return os.path.join(data_dir, username)


@pytest.fixture(scope='session')
def session_user_data_dir(data_dir, username):
    return os.path.join(data_dir, username)


@pytest.fixture
def database(user_data_dir, function_scope_messages_aggregator):
    return DBHandler(user_data_dir, '123', function_scope_messages_aggregator)
