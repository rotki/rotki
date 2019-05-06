import errno
import os
from collections import defaultdict

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.constants import YEAR_IN_SECONDS
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.history import PriceHistorian
from rotkehlchen.inquirer import Inquirer

TEST_HISTORY_DATA_START = "01/01/2015"


@pytest.fixture
def use_clean_caching_directory():
    """If this is set to True then a clean accounting directory will be used."""
    return False


@pytest.fixture
def accounting_data_dir(use_clean_caching_directory, tmpdir_factory):
    """For accounting we have a dedicated test data dir so that it's easy to
    cache the results of the historic price queries also in Travis"""
    if use_clean_caching_directory:
        return tmpdir_factory.mktemp('accounting_data')

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

    return data_directory


@pytest.fixture
def should_mock_price_queries():
    return True


@pytest.fixture
def mocked_price_queries():
    return defaultdict(defaultdict)


@pytest.fixture
def price_historian(
        accounting_data_dir,
        inquirer,
        should_mock_price_queries,
        mocked_price_queries,
):
    historian = PriceHistorian(
        data_directory=accounting_data_dir,
        history_date_start=TEST_HISTORY_DATA_START,
        cryptocompare=Cryptocompare(data_directory=accounting_data_dir),
    )
    if should_mock_price_queries:
        def mock_historical_price_query(from_asset, to_asset, timestamp):
            if from_asset == to_asset:
                return FVal(1)
            return mocked_price_queries[from_asset][to_asset][timestamp]

        historian.query_historical_price = mock_historical_price_query

    return historian


@pytest.fixture
def profit_currency():
    return A_EUR


@pytest.fixture
def accounting_create_csv():
    return False


@pytest.fixture
def accounting_ignored_assets():
    return []


@pytest.fixture
def accounting_include_crypto2crypto():
    return True


@pytest.fixture
def accounting_taxfree_after_period():
    return YEAR_IN_SECONDS


@pytest.fixture
def accounting_include_gas_costs():
    return True


@pytest.fixture
def accountant(
        price_historian,
        profit_currency,
        accounting_data_dir,
        accounting_create_csv,
        accounting_ignored_assets,
        accounting_include_crypto2crypto,
        accounting_taxfree_after_period,
        accounting_include_gas_costs,
):
    return Accountant(
        price_historian=price_historian,
        profit_currency=profit_currency,
        user_directory=accounting_data_dir,
        create_csv=accounting_create_csv,
        ignored_assets=accounting_ignored_assets,
        include_crypto2crypto=accounting_include_crypto2crypto,
        taxfree_after_period=accounting_taxfree_after_period,
        include_gas_costs=accounting_include_gas_costs,
    )


@pytest.fixture
def inquirer(accounting_data_dir):
    return Inquirer(data_dir=accounting_data_dir)


@pytest.fixture(scope='session')
def session_inquirer(session_data_dir):
    return Inquirer(data_dir=session_data_dir)
