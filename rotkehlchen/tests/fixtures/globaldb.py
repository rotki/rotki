import shutil
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.constants.misc import GLOBALDB_NAME, GLOBALDIR_NAME
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.globaldb.upgrades.manager import UPGRADES_LIST
from rotkehlchen.globaldb.utils import GLOBAL_DB_VERSION
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.database import mock_db_schema_sanity_check
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.globaldb import patch_for_globaldb_upgrade_to
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.globaldb.migrations.manager import MigrationRecord
    from rotkehlchen.utils.upgrades import UpgradeRecord


@pytest.fixture(name='generatable_user_ethereum_tokens')
def fixture_generatable_user_ethereum_tokens() -> bool:
    return False


@pytest.fixture(name='user_ethereum_tokens')
def fixture_user_ethereum_tokens() -> list[EvmToken] | Callable | None:
    return None


@pytest.fixture(name='reload_user_assets')
def fixture_reload_user_assets() -> bool:
    return True


@pytest.fixture(name='target_globaldb_version')
def fixture_target_globaldb_version() -> int:
    return GLOBAL_DB_VERSION


@pytest.fixture(name='globaldb_upgrades')
def fixture_globaldb_upgrades() -> list['UpgradeRecord']:
    return UPGRADES_LIST


@pytest.fixture(name='globaldb_migrations')
def fixture_globaldb_migrations() -> list['MigrationRecord']:
    return []


@pytest.fixture(name='run_globaldb_migrations')
def fixture_run_globaldb_migrations() -> bool:
    """Run the given globalDB migrations list or not.
    If not then last_migration_version is never written in the DB"""
    return True


@pytest.fixture(name='empty_global_addressbook')
def fixture_empty_global_addressbook() -> bool:
    """Whether to clear addressbook in the globaldb or not"""
    return False


@pytest.fixture(name='remove_global_assets')
def fixture_remove_global_assets() -> list[str]:
    """Asset identifiers to remove from the globalDB"""
    return []


@pytest.fixture(name='load_global_caches')
def fixture_load_global_caches() -> list[str]:
    """A list of counterparties of the decoders for which the global cache should be loaded."""
    return []


async def create_globaldb(
        data_directory,
        sql_vm_instructions_cb,
        messages_aggregator,
        perform_assets_updates=False,
) -> GlobalDBHandler:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    GlobalDBHandler._GlobalDBHandler__instance = None  # type: ignore

    # GlobalDBHandler now requires async initialization
    globaldb = await GlobalDBHandler.create_globaldb_instance(
        data_dir=data_directory,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        msg_aggregator=messages_aggregator,
        perform_assets_updates=perform_assets_updates,
    )
    return globaldb


async def _initialize_fixture_globaldb(
        custom_globaldb,
        tmpdir_factory,
        sql_vm_instructions_cb: int,
        reload_user_assets,
        target_globaldb_version,
        globaldb_upgrades,
        globaldb_migrations,
        run_globaldb_migrations,
        empty_global_addressbook,
        remove_global_assets,
        load_global_caches,
        messages_aggregator,
) -> tuple[GlobalDBHandler, Path]:
    # clean the previous resolver memory cache, as it
    # may have cached results from a discarded database
    root_dir = Path(__file__).resolve().parent.parent.parent
    if custom_globaldb is None:  # no specific version -- normal test
        source_db_path = root_dir / 'data' / GLOBALDB_NAME
    else:
        source_db_path = root_dir / 'tests' / 'data' / custom_globaldb
    new_data_dir = Path(tmpdir_factory.mktemp('test_data_dir'))
    new_global_dir = new_data_dir / GLOBALDIR_NAME
    new_global_dir.mkdir(parents=True, exist_ok=True)
    copyfile(source_db_path, new_global_dir / GLOBALDB_NAME)
    with ExitStack() as stack:
        stack.enter_context(
            patch('rotkehlchen.globaldb.migrations.manager.MIGRATIONS_LIST', globaldb_migrations),
        )
        if run_globaldb_migrations is False:
            stack.enter_context(
                patch('rotkehlchen.globaldb.upgrades.manager.maybe_apply_globaldb_migrations', side_effect=lambda *args: None),  # noqa: E501
            )
        if reload_user_assets is False:
            stack.enter_context(
                patch('rotkehlchen.globaldb.upgrades.manager.UPGRADES_LIST', globaldb_upgrades),
            )
            stack.enter_context(
                patch('rotkehlchen.globaldb.utils.GLOBAL_DB_VERSION', target_globaldb_version),
            )
        if target_globaldb_version != GLOBAL_DB_VERSION:
            stack.enter_context(mock_db_schema_sanity_check())
            patch_for_globaldb_upgrade_to(stack, target_globaldb_version)

        stack.enter_context(patch_decoder_reload_data(load_global_caches))
        globaldb = await create_globaldb(
            data_directory=new_data_dir,
            sql_vm_instructions_cb=0,
            messages_aggregator=messages_aggregator,
        )

    if empty_global_addressbook is True:
        async with globaldb.conn.write_ctx() as cursor:
            await cursor.execute('DELETE FROM address_book')

    if len(remove_global_assets) > 0:
        async with globaldb.conn.write_ctx() as cursor:
            await cursor.executemany(
                'DELETE FROM assets WHERE identifier=?;',
                [(asset,) for asset in remove_global_assets],
            )

    return globaldb, new_data_dir


@pytest.fixture(name='globaldb')
async def fixture_globaldb(
        custom_globaldb,
        tmpdir_factory,
        sql_vm_instructions_cb,
        reload_user_assets,
        target_globaldb_version,
        globaldb_upgrades,
        globaldb_migrations,
        run_globaldb_migrations,
        empty_global_addressbook,
        remove_global_assets,
        load_global_caches,
        messages_aggregator,
):
    globaldb, new_data_dir = await _initialize_fixture_globaldb(
        custom_globaldb=custom_globaldb,
        tmpdir_factory=tmpdir_factory,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        reload_user_assets=reload_user_assets,
        target_globaldb_version=target_globaldb_version,
        globaldb_upgrades=globaldb_upgrades,
        globaldb_migrations=globaldb_migrations,
        run_globaldb_migrations=run_globaldb_migrations,
        empty_global_addressbook=empty_global_addressbook,
        remove_global_assets=remove_global_assets,
        load_global_caches=load_global_caches,
        messages_aggregator=messages_aggregator,
    )
    yield globaldb

    await globaldb.cleanup()
    shutil.rmtree(new_data_dir)


@pytest.fixture(name='custom_globaldb')
def fixture_custom_globaldb() -> int | None:
    return None


@pytest.fixture(name='historical_price_test_data')
async def fixture_historical_price_test_data(globaldb):
    data = [HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1428994442),
        price=Price(FVal(210.865)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1439048640),
        price=Price(FVal(1.13)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1511626623),
        price=Price(FVal(396.56)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1511626622),
        price=Price(FVal(394.56)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1539713117),
        price=Price(FVal(178.615)),
    ), HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1539713117),
        price=Price(FVal(5626.17)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481088),
        price=Price(FVal(2044.76)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481095),
        price=Price(FVal(2045.76)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481101),
        price=Price(FVal(2049.76)),
    ), HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481102),
        price=Price(FVal(52342.5)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481103),
        price=Price(FVal(2049.96)),
    ), HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481196),
        price=Price(FVal(2085.76)),
    )]
    await globaldb.add_historical_prices(data)
