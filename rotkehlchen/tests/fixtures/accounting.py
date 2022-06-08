import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.chain.ethereum.accounting.aggregator import EVMAccountingAggregator
from rotkehlchen.chain.ethereum.oracles.saddle import SaddleOracle
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants import ONE
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import Timestamp


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
    (data_directory / 'assets').unlink(missing_ok=True)

    # Remove any old accounts. The only reason we keep this directory around is for
    # cached price queries, not for user DBs
    for x in data_directory.iterdir():
        directory_with_db = (
            x.is_dir() and
            (x / 'rotkehlchen.db').exists() or (x / 'rotkehlchen_transient.db').exists()
        )
        if directory_with_db:
            shutil.rmtree(x, ignore_errors=True)

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


@pytest.fixture(name='accounting_initialize_parameters')
def fixture_accounting_initialize_parameters():
    """
    If True initialize the DB parameters of the accountant and the events

    Normally they are initialized at the start of process_history, but if the
    test does not go there and is a unit test then we need to do it ourselves for the test
    """
    return False


@pytest.fixture(name='evm_accounting_aggregator')
def fixture_evm_accounting_aggregator(
        ethereum_manager,
        function_scope_messages_aggregator,
) -> EVMAccountingAggregator:
    return EVMAccountingAggregator(
        ethereum_manager=ethereum_manager,
        msg_aggregator=function_scope_messages_aggregator,
    )


@pytest.fixture(name='accountant')
def fixture_accountant(
        price_historian,  # pylint: disable=unused-argument
        database,
        function_scope_messages_aggregator,
        start_with_logged_in_user,
        accounting_initialize_parameters,
        evm_accounting_aggregator,
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
        evm_accounting_aggregator=evm_accounting_aggregator,
        msg_aggregator=function_scope_messages_aggregator,
        premium=premium,
    )

    if accounting_initialize_parameters:
        db_settings = accountant.db.get_settings()
        for pot in accountant.pots:
            pot.reset(
                settings=db_settings,
                start_ts=Timestamp(0),
                end_ts=Timestamp(0),
                report_id=1,
            )
        accountant.csvexporter.reset(start_ts=Timestamp(0), end_ts=Timestamp(0))

    return accountant


@pytest.fixture(name='should_mock_current_price_queries')
def fixture_should_mock_current_price_queries():
    return True


@pytest.fixture(scope='session', name='session_should_mock_current_price_queries')
def fixture_session_should_mock_current_price_queries():
    return True


@pytest.fixture(name='ignore_mocked_prices_for')
def fixture_ignore_mocked_prices_for():
    return []


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
        ethereum_manager,
        ignore_mocked_prices_for=None,
) -> Inquirer:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None  # type: ignore
    # Get a cryptocompare without a DB since invoking DB fixture here causes problems
    # of existing user for some tests
    cryptocompare = Cryptocompare(data_directory=data_directory, database=None)
    gecko = Coingecko()
    inquirer = Inquirer(
        data_dir=data_directory,
        cryptocompare=cryptocompare,
        coingecko=gecko,
    )
    if ethereum_manager is not None:
        inquirer.inject_ethereum(ethereum_manager)
        uniswap_v2_oracle = UniswapV2Oracle(ethereum_manager)
        uniswap_v3_oracle = UniswapV3Oracle(ethereum_manager)
        saddle_oracle = SaddleOracle(ethereum_manager)
        Inquirer().add_defi_oracles(
            uniswap_v2=uniswap_v2_oracle,
            uniswap_v3=uniswap_v3_oracle,
            saddle=saddle_oracle,
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

    def mock_find_usd_price(asset, ignore_cache: bool = False):  # pylint: disable=unused-argument
        return mocked_prices.get(asset, FVal('1.5'))

    if ignore_mocked_prices_for is None:
        inquirer.find_price = mock_find_price  # type: ignore
        inquirer.find_usd_price = mock_find_usd_price  # type: ignore
    else:
        def mock_some_prices(from_asset, to_asset, ignore_cache=False):
            if from_asset.symbol in ignore_mocked_prices_for:
                return inquirer.find_price_old(from_asset, to_asset, ignore_cache)
            return mock_find_price(from_asset, to_asset, ignore_cache)

        def mock_some_usd_prices(asset, ignore_cache=False):
            if asset.symbol in ignore_mocked_prices_for:
                return inquirer.find_usd_price_old(asset, ignore_cache)
            return mock_find_usd_price(asset, ignore_cache)

        inquirer.find_price_old = inquirer.find_price  # type: ignore
        inquirer.find_usd_price_old = inquirer.find_usd_price  # type: ignore
        inquirer.find_price = mock_some_prices  # type: ignore
        inquirer.find_usd_price = mock_some_usd_prices  # type: ignore

    def mock_query_fiat_pair(base, quote):  # pylint: disable=unused-argument
        return ONE

    inquirer._query_fiat_pair = mock_query_fiat_pair  # type: ignore

    return inquirer


@pytest.fixture(name='inquirer')
def fixture_inquirer(
        data_dir,
        should_mock_current_price_queries,
        mocked_current_prices,
        current_price_oracles_order,
        ignore_mocked_prices_for,
):
    """This version of the inquirer doesn't make use of the defi oracles and is initialized
    with ethereum_manager as None. To make use of the defi oracles use `inquirer_defi`.
    The reason is that some tests became really slow because they exhausted the coingecko/cc
    oracles and used the defi ones.
    """
    return create_inquirer(
        data_directory=data_dir,
        should_mock_current_price_queries=should_mock_current_price_queries,
        mocked_prices=mocked_current_prices,
        current_price_oracles_order=current_price_oracles_order,
        ethereum_manager=None,
        ignore_mocked_prices_for=ignore_mocked_prices_for,
    )


@pytest.fixture(scope='session')
def session_inquirer(
        session_data_dir,
        session_should_mock_current_price_queries,
        session_mocked_current_prices,
        session_current_price_oracles_order,
):
    """
    The ethereum_manager argument is defined as None for the reasons explained in the
    `inquirer` fixture
    """
    return create_inquirer(
        data_directory=session_data_dir,
        should_mock_current_price_queries=session_should_mock_current_price_queries,
        mocked_prices=session_mocked_current_prices,
        current_price_oracles_order=session_current_price_oracles_order,
        ethereum_manager=None,
    )


@pytest.fixture(name='inquirer_defi')
def fixture_inquirer_defi(
        data_dir,
        should_mock_current_price_queries,
        mocked_current_prices,
        current_price_oracles_order,
        ignore_mocked_prices_for,
        ethereum_manager,
):
    """This fixture is different from `inquirer` just in the use of defi oracles to query
    prices. If you don't need to use the defi oracles it is faster to use the `inquirer` fixture.
    """
    return create_inquirer(
        data_directory=data_dir,
        should_mock_current_price_queries=should_mock_current_price_queries,
        mocked_prices=mocked_current_prices,
        current_price_oracles_order=current_price_oracles_order,
        ethereum_manager=ethereum_manager,
        ignore_mocked_prices_for=ignore_mocked_prices_for,
    )
