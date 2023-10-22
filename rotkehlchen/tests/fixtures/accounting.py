import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants import ONE
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.oracles.structures import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.inquirer import inquirer_inject_ethereum_set_order
from rotkehlchen.types import Timestamp
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='use_clean_caching_directory')
def fixture_use_clean_caching_directory():
    """If this is set to True then a clean test user directory will be used."""
    if sys.platform == 'win32':  # need clean data dir only in Windows TODO: Figure out why # noqa: E501
        return True
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


@pytest.fixture()
def default_mock_price_value() -> Optional[FVal]:
    """Determines test behavior If a mock price is not found

    If it's None, then test fails with an error. If it is any other
    value then this is returned by the price mocking function. It's used
    for tests where other price queries may happen apart from the ones we check
    but we never check them so we don't care about the price.
    """
    return None


@pytest.fixture()
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


@pytest.fixture(name='accountant')
def fixture_accountant(
        price_historian,  # pylint: disable=unused-argument
        database,
        function_scope_messages_aggregator,
        start_with_logged_in_user,
        accounting_initialize_parameters,
        blockchain,
        start_with_valid_premium,
        rotki_premium_credentials,
        username,
) -> Optional[Accountant]:
    if not start_with_logged_in_user:
        return None

    premium = None
    if start_with_valid_premium:
        premium = Premium(credentials=rotki_premium_credentials, username=username)

    accountant = Accountant(
        db=database,
        chains_aggregator=blockchain,
        msg_aggregator=function_scope_messages_aggregator,
        premium=premium,
    )

    if accounting_initialize_parameters:
        with accountant.db.conn.read_ctx() as cursor:
            db_settings = accountant.db.get_settings(cursor)
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


@pytest.fixture(name='ignore_mocked_prices_for')
def fixture_ignore_mocked_prices_for() -> Optional[list[str]]:
    """An optional list of asset identifiers to ignore mocking for"""
    return None


@pytest.fixture(name='mocked_current_prices')
def fixture_mocked_current_prices():
    return {}


@pytest.fixture(name='mocked_current_prices_with_oracles')
def fixture_mocked_current_prices_with_oracles():
    return {}


@pytest.fixture(name='current_price_oracles_order')
def fixture_current_price_oracles_order():
    return DEFAULT_CURRENT_PRICE_ORACLES_ORDER


def _create_inquirer(
        data_directory,
        should_mock_current_price_queries,
        mocked_prices,
        mocked_current_prices_with_oracles,
        current_price_oracles_order,
        ethereum_manager,
        add_defi_oracles,
        ignore_mocked_prices_for=None,
) -> Inquirer:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None  # type: ignore
    # Get a cryptocompare without a DB since invoking DB fixture here causes problems
    # of existing user for some tests
    inquirer = Inquirer(
        data_dir=data_directory,
        cryptocompare=Cryptocompare(data_directory=data_directory, database=None),
        coingecko=Coingecko(),
        defillama=Defillama(),
        manualcurrent=ManualCurrentOracle(),
        msg_aggregator=MessagesAggregator(),
    )

    mocked_methods = ('find_price', 'find_usd_price', 'find_price_and_oracle', 'find_usd_price_and_oracle', '_query_fiat_pair')  # noqa: E501
    for x in mocked_methods:  # restore Inquirer to original state if needed
        old = f'{x}_old'
        if (original_method := getattr(Inquirer, old, None)) is not None:
            setattr(Inquirer, x, staticmethod(original_method))
            delattr(Inquirer, old)

    if ethereum_manager is not None:
        inquirer_inject_ethereum_set_order(
            inquirer=inquirer,
            add_defi_oracles=add_defi_oracles,
            current_price_oracles_order=current_price_oracles_order,
            ethereum_manager=ethereum_manager,
        )

    inquirer.set_oracles_order(current_price_oracles_order)
    if not should_mock_current_price_queries:
        return inquirer

    def mock_find_price(
            from_asset,
            to_asset,
            ignore_cache: bool = False,  # pylint: disable=unused-argument
            coming_from_latest_price: bool = False,   # pylint: disable=unused-argument
    ):
        return mocked_prices.get((from_asset, to_asset), FVal('1.5'))

    def mock_find_usd_price(
            asset,
            ignore_cache: bool = False,  # pylint: disable=unused-argument
            coming_from_latest_price: bool = False,   # pylint: disable=unused-argument
    ):
        return mocked_prices.get(asset, FVal('1.5'))

    def mock_find_price_with_oracle(
            from_asset,
            to_asset,
            **kwargs,  # pylint: disable=unused-argument
    ):
        result = mocked_current_prices_with_oracles.get((from_asset, to_asset))
        if result is not None:  # check mocked_current_prices_with_oracles first
            return *result, False
        price, oracle = mocked_prices.get((from_asset, to_asset), (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
        return price, oracle, False

    def mock_find_usd_price_with_oracle(asset, ignore_cache: bool = False):  # pylint: disable=unused-argument
        price, oracle = mocked_prices.get(asset, (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))
        return price, oracle, False

    # Since we are not yielding here we are using a **really** hacky way in order to
    # achieve two things:
    # 1. We use both inquirer and Inquirer, so both the created object and the class object
    # in order to make sure calling methods in both ways is mocked.
    # 2. We keep the original methods saved so that they can both be used inside the
    # ignore_mocked_prices_for case, but also so that we can reset the Inquirer class object
    # (see start of _create_inquirer()
    for x in mocked_methods:  # since we are mocking here, take backup of all inquirer methods
        old = f'{x}_old'
        setattr(inquirer, old, getattr(inquirer, x))
        setattr(Inquirer, old, staticmethod(getattr(Inquirer, x)))

    if ignore_mocked_prices_for is None:
        Inquirer.find_price = inquirer.find_price = mock_find_price  # type: ignore
        Inquirer.find_usd_price = inquirer.find_usd_price = mock_find_usd_price  # type: ignore
        Inquirer.find_price_and_oracle = inquirer.find_price_and_oracle = mock_find_price_with_oracle  # type: ignore  # noqa: E501
        Inquirer.find_usd_price_and_oracle = inquirer.find_usd_price_and_oracle = mock_find_usd_price_with_oracle  # type: ignore  # noqa: E501

    else:
        def mock_some_prices(
                from_asset,
                to_asset,
                ignore_cache=False,
                coming_from_latest_price=False,
        ):
            if from_asset.identifier in ignore_mocked_prices_for:
                return inquirer.find_price_old(  # pylint: disable=no-member - dynamic attribute
                    from_asset=from_asset,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    coming_from_latest_price=coming_from_latest_price,
                )
            return mock_find_price(
                from_asset=from_asset,
                to_asset=to_asset,
                ignore_cache=ignore_cache,
                coming_from_latest_price=coming_from_latest_price,
            )

        def mock_some_usd_prices(
                asset,
                ignore_cache=False,
                coming_from_latest_price=False,
        ):
            if asset.identifier in ignore_mocked_prices_for:
                return inquirer.find_usd_price_old(  # pylint: disable=no-member  dynamic attribute
                    asset=asset,
                    ignore_cache=ignore_cache,
                    coming_from_latest_price=coming_from_latest_price,
                )
            return mock_find_usd_price(
                asset=asset,
                ignore_cache=ignore_cache,
                coming_from_latest_price=coming_from_latest_price,
            )

        def mock_prices_with_oracles(from_asset, to_asset, ignore_cache=False, coming_from_latest_price=False, match_main_currency=False):  # noqa: E501
            if from_asset.identifier in ignore_mocked_prices_for:
                return inquirer.find_price_and_oracle_old(  # pylint: disable=no-member - dynamic attribute
                    from_asset=from_asset,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    coming_from_latest_price=coming_from_latest_price,
                    match_main_currency=match_main_currency,
                )
            if len(mocked_current_prices_with_oracles) != 0:
                price, oracle = mocked_current_prices_with_oracles.get((from_asset, to_asset), (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
                return price, oracle, False
            price = mock_find_price(
                from_asset=from_asset,
                to_asset=to_asset,
                ignore_cache=ignore_cache,
                coming_from_latest_price=coming_from_latest_price,
            )
            return price, CurrentPriceOracle.BLOCKCHAIN, False

        def mock_usd_prices_with_oracles(asset, ignore_cache=False, coming_from_latest_price=False, match_main_currency=False):  # noqa: E501
            if asset.identifier in ignore_mocked_prices_for:
                return inquirer.find_usd_price_and_oracle_old(  # pylint: disable=no-member - dynamic attribute
                    asset=asset,
                    ignore_cache=ignore_cache,
                    coming_from_latest_price=coming_from_latest_price,
                    match_main_currency=match_main_currency,
                )
            if len(mocked_current_prices_with_oracles) != 0:
                price, oracle = mocked_current_prices_with_oracles.get(asset, (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
                return price, oracle, False
            price = mock_find_usd_price(
                asset=asset,
                ignore_cache=ignore_cache,
                coming_from_latest_price=coming_from_latest_price,
            )
            return price, CurrentPriceOracle.BLOCKCHAIN, False

        inquirer.find_price = Inquirer.find_price = mock_some_prices  # type: ignore
        inquirer.find_usd_price = Inquirer.find_usd_price = mock_some_usd_prices  # type: ignore
        inquirer.find_price_and_oracle = Inquirer.find_price_and_oracle = mock_prices_with_oracles  # type: ignore
        inquirer.find_usd_price_and_oracle = Inquirer.find_usd_price_and_oracle = mock_usd_prices_with_oracles  # type: ignore  # noqa: E501

    def mock_query_fiat_pair(*args, **kwargs):  # pylint: disable=unused-argument
        return (ONE, CurrentPriceOracle.FIAT)

    inquirer._query_fiat_pair = Inquirer._query_fiat_pair = mock_query_fiat_pair  # type: ignore

    return inquirer


@pytest.fixture(name='inquirer')
def fixture_inquirer(
        globaldb,  # pylint: disable=unused-argument  # needed for _create_inquirer
        data_dir,
        should_mock_current_price_queries,
        mocked_current_prices,
        mocked_current_prices_with_oracles,
        current_price_oracles_order,
        ignore_mocked_prices_for,
):
    """This version of the inquirer doesn't make use of the defi oracles.
    To make use of the defi oracles use `inquirer_defi`. The reason is that some
    tests became really slow because they exhausted the coingecko/cc
    oracles and used the defi ones.
    """
    return _create_inquirer(
        data_directory=data_dir,
        should_mock_current_price_queries=should_mock_current_price_queries,
        mocked_prices=mocked_current_prices,
        mocked_current_prices_with_oracles=mocked_current_prices_with_oracles,
        current_price_oracles_order=current_price_oracles_order,
        add_defi_oracles=False,
        ethereum_manager=None,
        ignore_mocked_prices_for=ignore_mocked_prices_for,
    )


@pytest.fixture(name='inquirer_defi')
def fixture_inquirer_defi(
        globaldb,  # pylint: disable=unused-argument  # needed for _create_inquirer
        data_dir,
        should_mock_current_price_queries,
        mocked_current_prices,
        mocked_current_prices_with_oracles,
        current_price_oracles_order,
        ignore_mocked_prices_for,
        ethereum_manager,
):
    """This fixture is different from `inquirer` just in the use of defi oracles to query
    prices. If you don't need to use the defi oracles it is faster to use the `inquirer` fixture.
    """
    return _create_inquirer(
        data_directory=data_dir,
        should_mock_current_price_queries=should_mock_current_price_queries,
        mocked_prices=mocked_current_prices,
        mocked_current_prices_with_oracles=mocked_current_prices_with_oracles,
        current_price_oracles_order=current_price_oracles_order,
        ethereum_manager=ethereum_manager,
        add_defi_oracles=True,
        ignore_mocked_prices_for=ignore_mocked_prices_for,
    )
