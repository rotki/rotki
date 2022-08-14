from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, Callable, List, Mapping, Optional
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.globaldb.handler import DB_UPGRADES, GLOBAL_DB_VERSION
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


@pytest.fixture(name='custom_ethereum_tokens')
def fixture_custom_ethereum_tokens() -> Optional[List[EvmToken]]:
    return None


@pytest.fixture(name='reaload_custom_assets')
def fixture_reaload_custom_assets() -> bool:
    return True


@pytest.fixture(name='target_globaldb_version')
def fixture_target_globaldb_version() -> int:
    return GLOBAL_DB_VERSION


@pytest.fixture(name='db_upgrades')
def fixture_db_upgrades() -> Mapping[int, Callable[['DBConnection'], None]]:
    return DB_UPGRADES


def create_globaldb(
        data_directory,
        sql_vm_instructions_cb,
) -> GlobalDBHandler:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    GlobalDBHandler._GlobalDBHandler__instance = None  # type: ignore

    handler = GlobalDBHandler(data_dir=data_directory, sql_vm_instructions_cb=sql_vm_instructions_cb)  # noqa: E501
    return handler


@pytest.fixture(name='globaldb')
def fixture_globaldb(
        globaldb_version,
        tmpdir_factory,
        sql_vm_instructions_cb,
        reaload_custom_assets,
        target_globaldb_version,
        db_upgrades,
):
    # clean the previous resolver memory cache, as it
    # may have cached results from a discarded database
    AssetResolver().clean_memory_cache()
    root_dir = Path(__file__).resolve().parent.parent.parent
    if globaldb_version is None:  # no specific version -- normal test
        source_db_path = root_dir / 'data' / 'global.db'
    else:
        source_db_path = root_dir / 'tests' / 'data' / f'v{globaldb_version}_global.db'
    new_data_dir = Path(tmpdir_factory.mktemp('test_data_dir'))
    new_global_dir = new_data_dir / 'global_data'
    new_global_dir.mkdir(parents=True, exist_ok=True)
    copyfile(source_db_path, new_global_dir / 'global.db')
    if reaload_custom_assets is False:
        with (
            patch('rotkehlchen.globaldb.handler._reload_constant_assets', lambda *a, **k: None),
            patch('rotkehlchen.globaldb.handler.DB_UPGRADES', db_upgrades),
            patch('rotkehlchen.globaldb.handler.GLOBAL_DB_VERSION', target_globaldb_version),
        ):
            return create_globaldb(new_data_dir, sql_vm_instructions_cb)
    return create_globaldb(new_data_dir, sql_vm_instructions_cb)


@pytest.fixture(name='globaldb_version')
def fixture_globaldb_version() -> Optional[int]:
    return None


@pytest.fixture(name='historical_price_test_data')
def fixture_historical_price_test_data(globaldb):
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
    globaldb.add_historical_prices(data)
