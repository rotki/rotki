import pytest
import os
import errno

from rotkehlchen.history import PriceHistorian
from rotkehlchen.accounting import Accountant

TEST_HISTORY_DATA_START = "01/01/2015"


@pytest.fixture
def accounting_data_dir():
    """For accounting we have a dedicated test data dir so that it's easy to
    cache the results of the historic price queries also in Travis"""
    home = os.path.expanduser("~")
    if 'TRAVIS' in os.environ:
        data_directory = os.path.join(home, '.cache', '.rotkehlchen-test-dir')
    else:
        data_directory = os.path.join(home, '.rotkehlchen', 'testadata')

    try:
        os.makedirs(data_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    return data_directory


@pytest.fixture
def price_historian(accounting_data_dir):
    return PriceHistorian(accounting_data_dir, TEST_HISTORY_DATA_START)


@pytest.fixture
def profit_currency():
    return 'EUR'


@pytest.fixture
def accounting_create_csv():
    return False


@pytest.fixture
def accounting_ignored_assets():
    return []


@pytest.fixture
def accountant(
        price_historian,
        profit_currency,
        accounting_data_dir,
        accounting_create_csv,
        accounting_ignored_assets
):
    return Accountant(
        price_historian=price_historian,
        profit_currency=profit_currency,
        user_directory=accounting_data_dir,
        create_csv=accounting_create_csv,
        ignored_assets=accounting_ignored_assets
    )
