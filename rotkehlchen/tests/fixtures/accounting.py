import errno
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer


@pytest.fixture
def use_clean_caching_directory():
    """If this is set to True then a clean test user directory will be used."""
    return False


@pytest.fixture
def data_dir(use_clean_caching_directory, tmpdir_factory) -> Path:
    """The tests data dir is peristent so that we can cache price queries between
    tests. If use_clean_caching_directory is True then a completely fresh dir is returned"""
    if use_clean_caching_directory:
        return Path(tmpdir_factory.mktemp('test_data_dir'))

    home = os.path.expanduser("~")
    if 'CI' in os.environ:
        data_directory = os.path.join(home, '.cache', '.rotkehlchen-test-dir')
    else:
        data_directory = os.path.join(home, '.rotkehlchen', 'tests_data_directory')

    try:
        os.makedirs(data_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Remove any old accounts. The only reason we keep this directory around is for
    # cached price queries, not for user DBs
    data_dir = Path(data_directory)
    for x in data_dir.iterdir():
        if x.is_dir() and (x / 'rotkehlchen.db').exists():
            shutil.rmtree(x)

    return data_dir


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
        data_dir,
        accounting_create_csv,
        function_scope_messages_aggregator,
        start_with_logged_in_user,
        accounting_initialize_parameters,
) -> Optional[Accountant]:
    if not start_with_logged_in_user:
        return None

    accountant = Accountant(
        db=database,
        user_directory=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        create_csv=accounting_create_csv,
    )

    if accounting_initialize_parameters:
        db_settings = accountant.db.get_settings()
        accountant._customize(db_settings)

    return accountant


@pytest.fixture
def should_mock_current_price_queries():
    return True


@pytest.fixture(scope='session')
def session_should_mock_current_price_queries():
    return True


@pytest.fixture
def mocked_current_prices():
    return {}


@pytest.fixture(scope='session')
def session_mocked_current_prices():
    return {}


def create_inquirer(data_dir, should_mock_current_price_queries, mocked_prices) -> Inquirer:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None  # type: ignore
    # Get a cryptocompare without a DB since invoking DB fixture here causes problems
    # of existing user for some tests
    cryptocompare = Cryptocompare(data_directory=data_dir, database=None)
    inquirer = Inquirer(data_dir=data_dir, cryptocompare=cryptocompare)
    if not should_mock_current_price_queries:
        return inquirer

    def mock_find_usd_price(asset):  # pylint: disable=unused-argument
        return mocked_prices.get(asset, FVal('1.5'))

    inquirer.find_usd_price = mock_find_usd_price  # type: ignore

    def mock_query_fiat_pair(base, quote):  # pylint: disable=unused-argument
        return FVal(1)

    inquirer.query_fiat_pair = mock_query_fiat_pair  # type: ignore

    return inquirer


@pytest.fixture
def inquirer(data_dir, should_mock_current_price_queries, mocked_current_prices):
    return create_inquirer(data_dir, should_mock_current_price_queries, mocked_current_prices)


@pytest.fixture(scope='session')
def session_inquirer(
        session_data_dir,
        session_should_mock_current_price_queries,
        session_mocked_current_prices,
):
    return create_inquirer(
        session_data_dir,
        session_should_mock_current_price_queries,
        session_mocked_current_prices,
    )
