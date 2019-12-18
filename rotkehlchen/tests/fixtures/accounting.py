import errno
import os
from collections import defaultdict
from typing import Optional

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import FilePath


@pytest.fixture
def use_clean_caching_directory():
    """If this is set to True then a clean test user directory will be used."""
    return False


@pytest.fixture
def accounting_data_dir(use_clean_caching_directory, tmpdir_factory) -> FilePath:
    """For accounting we have a dedicated test data dir so that it's easy to
    cache the results of the historic price queries also in Travis"""
    if use_clean_caching_directory:
        return FilePath(tmpdir_factory.mktemp('accounting_data'))

    home = os.path.expanduser("~")
    if 'TRAVIS' in os.environ:
        data_directory = os.path.join(home, '.cache', '.rotkehlchen-test-dir')
    else:
        data_directory = os.path.join(home, '.rotkehlchen', 'tests_data_directory')

    try:
        os.makedirs(data_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    return FilePath(data_directory)


@pytest.fixture
def should_mock_price_queries():
    return True


@pytest.fixture
def mocked_price_queries():
    return defaultdict(defaultdict)


@pytest.fixture
def accounting_create_csv():
    # TODO: The whole create_csv argument should be deleted.
    # Or renamed. Since it's not about actually creating the CSV
    # but keeping the events in memory
    return True


@pytest.fixture
def accounting_initialize_parameters():
    """
    If True initialize the DB parameters of the accountant and the events

    Normally they are initialized at the start of process_history, but if the
    test does not go there and is a unit test then we need to do it ourselves for the test
    """
    return False


@pytest.fixture
def accountant(
        price_historian,  # pylint: disable=unused-argument
        database,
        accounting_data_dir,
        accounting_create_csv,
        messages_aggregator,
        start_with_logged_in_user,
        accounting_initialize_parameters,
) -> Optional[Accountant]:
    if not start_with_logged_in_user:
        return None

    accountant = Accountant(
        db=database,
        user_directory=accounting_data_dir,
        msg_aggregator=messages_aggregator,
        create_csv=accounting_create_csv,
    )

    if accounting_initialize_parameters:
        db_settings = accountant.db.get_settings()
        accountant._customize(db_settings)

    return accountant


@pytest.fixture
def inquirer(accounting_data_dir):
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None
    return Inquirer(data_dir=accounting_data_dir)


@pytest.fixture(scope='session')
def session_inquirer(session_data_dir):
    return Inquirer(data_dir=session_data_dir)
