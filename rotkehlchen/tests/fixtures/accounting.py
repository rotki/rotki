import json
import os
import shutil
import sys
from collections import defaultdict
from collections.abc import Generator
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants import ONE
from rotkehlchen.constants.misc import USERSDIR_NAME
from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.oracles.structures import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.constants import CURRENT_PRICE_MOCK
from rotkehlchen.tests.utils.inquirer import inquirer_inject_evm_managers_set_order
from rotkehlchen.types import Timestamp
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(name='use_clean_caching_directory')
def fixture_use_clean_caching_directory():
    """If this is set to True then a clean test user directory will be used."""
    if sys.platform == 'win32':  # need clean data dir only in Windows TODO: Figure out why # noqa: E501
        return True
    return False


@pytest.fixture(name='data_dir')
def fixture_data_dir(use_clean_caching_directory, tmpdir_factory, worker_id) -> Generator[Path | None, None, None]:  # noqa: E501
    """The tests data dir is persistent so that we can cache global DB.
    Adjusted from old code. Not sure if it makes sense to keep. Could also just
    force clean caching directory everywhere"""
    if use_clean_caching_directory:
        path = Path(tmpdir_factory.mktemp('test_data_dir'))
        yield path
        shutil.rmtree(path, ignore_errors=sys.platform == 'win32')
    else:
        if 'CI' in os.environ:
            data_directory = Path.home() / '.cache' / '.rotkehlchen-test-dir'
        else:
            data_directory = default_data_directory().parent / 'test_data'

        if worker_id != 'master':
            # when running the test in parallel use a path based in the worker id to avoid
            # conflicts between workers
            data_directory /= worker_id

        data_directory.mkdir(parents=True, exist_ok=True)
        # But always reset users
        shutil.rmtree(data_directory / USERSDIR_NAME, ignore_errors=True)

        yield data_directory


@pytest.fixture(name='should_mock_price_queries')
def fixture_should_mock_price_queries():
    return True


@pytest.fixture
def default_mock_price_value() -> FVal | None:
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


@pytest.fixture(name='initialize_accounting_rules')
def fixture_initialize_accounting_rules() -> bool:
    """
    If set to False then the fixtures that build the accountant from scratch won't load the
    accounting rules to the database. It is the case for the rotkehlchen_api_server and its
    variants.
    """
    return False


@pytest.fixture(name='accountant_without_rules')
def fixture_accountant_without_rules() -> bool:
    """
    If set to False the accountant fixture will be initialized without pre-loaded rules
    """
    return False


@pytest.fixture(name='use_dummy_pot')
def fixture_use_dummy_pot() -> bool:
    """
    If set to true then we will initialize the pot in accounting as a dummy pot
    """
    return False


@pytest.fixture(name='last_accounting_rules_version', scope='session')
def fixture_last_accounting_rules_version() -> int:
    return 5


@pytest.fixture(name='latest_accounting_rules', autouse=True, scope='session')
def fixture_download_rules(last_accounting_rules_version) -> list[tuple[int, Path]]:
    """
    Gets the paths to the files containing the accounting rules as the RotkiDataUpdater ingest
    them. For each update file, if the files doesn't exist it is downloaded from github. Until we
    reach the last_acounting_rules_version.

    Returns a list of tuples. (version, update_json_file_path)
    """
    root_dir = default_data_directory().parent / 'test-caching'
    base_dir = root_dir / 'accounting_rules'
    result = []
    for i in range(1, last_accounting_rules_version + 1):
        rules_file = Path(base_dir / f'v{i}.json')
        if (rules_file := Path(base_dir / f'v{i}.json')).exists():
            result.append((i, rules_file))
            continue

        response = requests.get(f'https://raw.githubusercontent.com/rotki/data/develop/updates/accounting_rules/v{i}.json')
        rules_file.parent.mkdir(exist_ok=True, parents=True)
        rules_file.write_text(response.text, encoding='utf-8')
        result.append((i, rules_file))

    return result


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
        latest_accounting_rules,
        accountant_without_rules,
        use_dummy_pot,
) -> Accountant | None:
    if not start_with_logged_in_user:
        return None

    premium = None
    if start_with_valid_premium:
        premium = Premium(credentials=rotki_premium_credentials, username=username)

    # add accounting rules to the database
    data_updater = RotkiDataUpdater(
        msg_aggregator=function_scope_messages_aggregator,
        user_db=database,
    )

    if accountant_without_rules is False:
        for version, jsonfile in latest_accounting_rules:
            data_updater.update_accounting_rules(
                data=json.loads(jsonfile.read_text(encoding='utf-8'))['accounting_rules'],
                version=version,
            )

    with ExitStack() as stack:
        if use_dummy_pot:  # don't load ignored assets if dummy
            stack.enter_context(patch.object(database, 'get_ignored_asset_ids', lambda _: set()))

        with stack:
            accountant = Accountant(
                db=database,
                chains_aggregator=blockchain,
                msg_aggregator=function_scope_messages_aggregator,
                premium=premium,
            )

        if use_dummy_pot:  # set the dummy behavior
            accountant.pots[0].is_dummy_pot = use_dummy_pot

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
def fixture_ignore_mocked_prices_for() -> list[str] | None:
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
        evm_managers,
        add_defi_oracles,
        ignore_mocked_prices_for=None,
) -> Inquirer:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    Inquirer._Inquirer__instance = None  # type: ignore
    # Get a defillama,cryptocompare etc without a DB since invoking DB fixture here causes problems
    # of existing user for some tests
    inquirer = Inquirer(
        data_dir=data_directory,
        cryptocompare=Cryptocompare(database=None),
        coingecko=Coingecko(database=None),
        defillama=Defillama(database=None),
        alchemy=Alchemy(database=None),
        manualcurrent=ManualCurrentOracle(),
        msg_aggregator=MessagesAggregator(),
    )

    mocked_methods = ('find_prices', 'find_usd_prices', 'find_prices_and_oracles', 'find_usd_prices_and_oracles', '_query_fiat_pair')  # noqa: E501
    for x in mocked_methods:  # restore Inquirer to original state if needed
        old = f'{x}_old'
        if (original_method := getattr(Inquirer, old, None)) is not None:
            setattr(Inquirer, x, staticmethod(original_method))
            delattr(Inquirer, old)

    if len(evm_managers) > 0:
        inquirer_inject_evm_managers_set_order(
            inquirer=inquirer,
            add_defi_oracles=add_defi_oracles,
            current_price_oracles_order=current_price_oracles_order,
            evm_managers=evm_managers,
        )

    inquirer.set_oracles_order(current_price_oracles_order)
    if not should_mock_current_price_queries:
        return inquirer

    def mock_find_prices(
            from_assets,
            to_asset,
            ignore_cache: bool = False,  # pylint: disable=unused-argument
            skip_onchain: bool = False,  # pylint: disable=unused-argument
    ):
        return {
            from_asset: mocked_prices.get((from_asset, to_asset), FVal('1.5'))
            for from_asset in from_assets
        }

    def mock_find_usd_prices(
            assets,
            ignore_cache: bool = False,  # pylint: disable=unused-argument
            skip_onchain: bool = False,  # pylint: disable=unused-argument
    ):
        return {
            asset: mocked_prices.get(asset, FVal('1.5'))
            for asset in assets
        }

    def mock_find_prices_with_oracles(
            from_assets,
            to_asset,
            **kwargs,  # pylint: disable=unused-argument
    ):
        return {
            from_asset: (
                mocked_current_prices_with_oracles.get((from_asset, to_asset))
                if (from_asset, to_asset) in mocked_current_prices_with_oracles else
                mocked_prices.get((from_asset, to_asset), (CURRENT_PRICE_MOCK, CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
            )
            for from_asset in from_assets
        }

    def mock_find_usd_prices_with_oracles(assets, **kwargs):  # pylint: disable=unused-argument
        return {
            asset: (mocked_prices.get(asset, FVal('1.5')), CurrentPriceOracle.BLOCKCHAIN)
            for asset in assets
        }

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
        Inquirer.find_prices = inquirer.find_prices = mock_find_prices  # type: ignore
        Inquirer.find_usd_prices = inquirer.find_usd_prices = mock_find_usd_prices  # type: ignore
        Inquirer.find_prices_and_oracles = inquirer.find_prices_and_oracles = mock_find_prices_with_oracles  # type: ignore  # noqa: E501
        Inquirer.find_usd_prices_and_oracles = inquirer.find_usd_prices_and_oracles = mock_find_usd_prices_with_oracles  # type: ignore  # noqa: E501

    else:
        def get_assets_to_mock(assets):
            mock_assets = []
            normal_assets = []
            for asset in assets:
                if asset.identifier in ignore_mocked_prices_for:
                    normal_assets.append(asset)
                else:
                    mock_assets.append(asset)

            return normal_assets, mock_assets

        def mock_some_prices(
                from_assets,
                to_asset,
                ignore_cache=False,
                skip_onchain=False,
        ):
            normal_assets, mock_assets = get_assets_to_mock(assets=from_assets)
            prices = {}
            if len(normal_assets) > 0:
                prices.update(inquirer.find_prices_old(  # pylint: disable=no-member # dynamic attribute
                    from_assets=normal_assets,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            if len(mock_assets) > 0:
                prices.update(mock_find_prices(
                    from_assets=mock_assets,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            return prices

        def mock_some_usd_prices(
                assets,
                ignore_cache=False,
                skip_onchain=False,
        ):
            normal_assets, mock_assets = get_assets_to_mock(assets=assets)
            prices = {}
            if len(normal_assets) > 0:
                prices.update(inquirer.find_usd_prices_old(  # pylint: disable=no-member # dynamic attribute
                    assets=normal_assets,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            if len(mock_assets) > 0:
                prices.update(mock_find_usd_prices(
                    assets=mock_assets,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            return prices

        def mock_prices_with_oracles(
                from_assets,
                to_asset,
                ignore_cache=False,
                skip_onchain=False,
        ):
            normal_assets, mock_assets = get_assets_to_mock(assets=from_assets)
            prices = {}
            if len(normal_assets) > 0:
                prices.update(inquirer.find_prices_and_oracles_old(  # pylint: disable=no-member # dynamic attribute
                    from_assets=normal_assets,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            if len(mocked_current_prices_with_oracles) != 0:
                prices.update({
                    from_asset: mocked_current_prices_with_oracles.get((from_asset, to_asset), (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
                    for from_asset in mock_assets
                })
                return prices
            if len(mock_assets) > 0:
                prices.update(mock_find_prices_with_oracles(
                    from_assets=mock_assets,
                    to_asset=to_asset,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            return prices

        def mock_usd_prices_with_oracles(assets, ignore_cache=False, skip_onchain=False):
            normal_assets, mock_assets = get_assets_to_mock(assets=assets)
            prices = {}
            if len(normal_assets) > 0:
                prices.update(inquirer.find_usd_prices_and_oracles_old(  # pylint: disable=no-member # dynamic attribute
                    assets=normal_assets,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            if len(mocked_current_prices_with_oracles) != 0:
                prices.update({
                    asset: mocked_current_prices_with_oracles.get(asset, (FVal('1.5'), CurrentPriceOracle.BLOCKCHAIN))  # noqa: E501
                    for asset in mock_assets
                })
                return prices
            if len(mock_assets) > 0:
                prices.update(mock_find_usd_prices_with_oracles(
                    assets=mock_assets,
                    ignore_cache=ignore_cache,
                    skip_onchain=skip_onchain,
                ))
            return prices

        inquirer.find_prices = Inquirer.find_prices = mock_some_prices  # type: ignore
        inquirer.find_usd_prices = Inquirer.find_usd_prices = mock_some_usd_prices  # type: ignore
        inquirer.find_prices_and_oracles = Inquirer.find_prices_and_oracles = mock_prices_with_oracles  # type: ignore  # noqa: E501
        inquirer.find_usd_prices_and_oracles = Inquirer.find_usd_prices_and_oracles = mock_usd_prices_with_oracles  # type: ignore  # noqa: E501

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
        evm_managers=[],
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
        polygon_pos_manager,
        arbitrum_one_manager,
        optimism_manager,
        base_manager,
        binance_sc_manager,
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
        evm_managers=[
            ethereum_manager,
            polygon_pos_manager,
            arbitrum_one_manager,
            optimism_manager,
            base_manager,
            binance_sc_manager,
        ],
        add_defi_oracles=True,
        ignore_mocked_prices_for=ignore_mocked_prices_for,
    )
