import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pytest

from rotkehlchen.premium.premium import Premium
from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.config import default_data_directory
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, Inquirer


@pytest.fixture(name='use_clean_caching_directory')
def fixture_use_clean_caching_directory():
    """If this is set to True then a clean test user directory will be used."""
    return False


@pytest.fixture(name='data_dir')
def fixture_data_dir(use_clean_caching_directory, tmpdir_factory) -> Path:
    """The tests data dir is peristent so that we can cache price queries between
    tests. If use_clean_caching_directory is True then a completely fresh dir is returned"""
    if use_clean_caching_directory:
        return Path(tmpdir_factory.mktemp('test_data_dir'))

    if 'CI' in os.environ:
        data_directory = Path.home() / '.cache' / '.rotkehlchen-test-dir'
    else:
        data_directory = default_data_directory().parent / 'test_data'

    data_directory.mkdir(parents=True, exist_ok=True)

    # do not keep pull github assets between tests. Can really confuse test results
    # as we may end up with different set of assets in tests
    try:
        (data_directory / 'assets').unlink()
    except FileNotFoundError:  # TODO: In python 3.8 we can add missing_ok=True to unlink
        pass

    # Remove any old accounts. The only reason we keep this directory around is for
    # cached price queries, not for user DBs
    for x in data_directory.iterdir():
        if x.is_dir() and (x / 'rotkehlchen.db').exists():
            shutil.rmtree(x)

    return data_directory


@pytest.fixture(name='should_mock_price_queries')
def fixture_should_mock_price_queries():
    return True


@pytest.fixture
def default_mock_price_value() -> Optional[FVal]:
    """Determines test behavior If a mock price is not found

    If it's None, then test fails with an error. If it is any other
    value then this is returned by the price mocking function. It's used
    for tests where other price queries may happen apart from the ones we check
    but we never check them so we don't care about the price.
    """
    return None


@pytest.fixture
def mocked_price_queries():
    return defaultdict(defaultdict)


@pytest.fixture(name='accounting_create_csv')
def fixture_accounting_create_csv():
    # TODO: The whole create_csv argument should be deleted.
    # Or renamed. Since it's not about actually creating the CSV
    # but keeping the events in memory
    return True


@pytest.fixture(name='accounting_initialize_parameters')
def fixture_accounting_initialize_parameters():
    """
    If True initialize the DB parameters of the accountant and the events

    Normally they are initialized at the start of process_history, but if the
    test does not go there and is a unit test then we need to do it ourselves for the test
    """
    return False


@pytest.fixture(name='accountant')
def fixture_accountant(
        price_historian,  # pylint: disable=unused-argument
        database,
        data_dir,
        accounting_create_csv,
        function_scope_messages_aggregator,
        start_with_logged_in_user,
        accounting_initialize_parameters,
        start_with_valid_premium,
        rotki_premium_credentials,
) -> Optional[Accountant]:
    if not start_with_logged_in_user:
        return None

    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    accountant = Accountant(
        db=database,
        user_directory=data_dir,
        msg_aggregator=function_scope_messages_aggregator,
        create_csv=accounting_create_csv,
        premium=premium,
    )

    if accounting_initialize_parameters:
        db_settings = accountant.db.get_settings()
        accountant._customize(db_settings)

    return accountant


@pytest.fixture(name='should_mock_current_price_queries')
def fixture_should_mock_current_price_queries():
    return True


@pytest.fixture(scope='session', name='session_should_mock_current_price_queries')
def fixture_session_should_mock_current_price_queries():
    return True


@pytest.fixture(name='mocked_current_prices')
def fixture_mocked_current_prices():
    return {}


@pytest.fixture(scope='session', name='session_mocked_current_prices')
def fixture_session_mocked_current_prices():
    return {}


@pytest.fixture(name='current_price_oracles_order')
def fixture_current_price_oracles_order():
    return DEFAULT_CURRENT_PRICE_ORACLES_ORDER


@pytest.fixture(scope='session', name='session_current_price_oracles_order')
def fixture_session_current_price_oracles_order():
    return DEFAULT_CURRENT_PRICE_ORACLES_ORDER


def create_inquirer(
        data_directory,
        should_mock_current_price_queries,
        mocked_prices,
        current_price_oracles_order,
) -> Inquirer:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None  # type: ignore
    # Get a cryptocompare without a DB since invoking DB fixture here causes problems
    # of existing user for some tests
    cryptocompare = Cryptocompare(data_directory=data_directory, database=None)
    gecko = Coingecko(data_directory=data_directory)
    inquirer = Inquirer(
        data_dir=data_directory,
        cryptocompare=cryptocompare,
        coingecko=gecko,
    )
    inquirer.set_oracles_order(current_price_oracles_order)

    if not should_mock_current_price_queries:
        return inquirer

    def mock_find_price(
            from_asset,
            to_asset,
            ignore_cache: bool = False,  # pylint: disable=unused-argument
    ):
        return mocked_prices.get((from_asset, to_asset), FVal('1.5'))

    inquirer.find_price = mock_find_price  # type: ignore

    def mock_find_usd_price(asset, ignore_cache: bool = False):  # pylint: disable=unused-argument
        return mocked_prices.get(asset, FVal('1.5'))

    inquirer.find_usd_price = mock_find_usd_price  # type: ignore

    def mock_query_fiat_pair(base, quote):  # pylint: disable=unused-argument
        return FVal(1)

    inquirer._query_fiat_pair = mock_query_fiat_pair  # type: ignore

    return inquirer


@pytest.fixture(name='inquirer')
def fixture_inquirer(
        data_dir,
        should_mock_current_price_queries,
        mocked_current_prices,
        current_price_oracles_order,
):
    return create_inquirer(
        data_directory=data_dir,
        should_mock_current_price_queries=should_mock_current_price_queries,
        mocked_prices=mocked_current_prices,
        current_price_oracles_order=current_price_oracles_order,
    )


@pytest.fixture(scope='session')
def session_inquirer(
        session_data_dir,
        session_should_mock_current_price_queries,
        session_mocked_current_prices,
        session_current_price_oracles_order,
):
    return create_inquirer(
        data_directory=session_data_dir,
        should_mock_current_price_queries=session_should_mock_current_price_queries,
        mocked_prices=session_mocked_current_prices,
        current_price_oracles_order=session_current_price_oracles_order,
    )
