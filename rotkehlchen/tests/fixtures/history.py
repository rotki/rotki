from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
from rotkehlchen.tests.utils.history import maybe_mock_historical_price_queries
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.fixture(name='cryptocompare')
def fixture_cryptocompare(database):
    return Cryptocompare(database=database)


@pytest.fixture(scope='session', name='session_coingecko')
def fixture_session_coingecko():
    return Coingecko(database=None)


@pytest.fixture(name='coingecko')
def fixture_coingecko():
    return Coingecko(database=None)


@pytest.fixture(name='alchemy')
def fixture_alchemy(database: 'DBHandler'):
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.ALCHEMY,
                api_key=ApiKey('dummy-api-key'),
            )],
        )
    return Alchemy(database=database)


@pytest.fixture(scope='session', name='session_defillama')
def fixture_session_defillama():
    return Defillama(database=None)


@pytest.fixture(name='defillama')
def fixture_defillama():
    return Defillama(database=None)


@pytest.fixture(name='uniswapv2_inquirer')
def fixture_uniswapv2():
    return UniswapV2Oracle()


@pytest.fixture(name='uniswapv3_inquirer')
def fixture_uniswapv3():
    return UniswapV3Oracle()


@pytest.fixture(name='historical_price_oracles_order')
def fixture_historical_price_oracles_order():
    return DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER


@pytest.fixture(name='dont_mock_price_for')
def fixture_dont_mock_price_for():
    return []


@pytest.fixture(name='force_no_price_found_for')
def fixture_force_no_price_found_for():
    return []


@pytest.fixture
def price_historian(
        data_dir,
        inquirer_defi,  # pylint: disable=unused-argument
        should_mock_price_queries,
        mocked_price_queries,
        cryptocompare,
        coingecko,
        alchemy,
        defillama,
        uniswapv2_inquirer,
        uniswapv3_inquirer,
        default_mock_price_value,
        historical_price_oracles_order,
        dont_mock_price_for,
        force_no_price_found_for,
):
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None
    historian = PriceHistorian(
        data_directory=data_dir,
        cryptocompare=cryptocompare,
        coingecko=coingecko,
        alchemy=alchemy,
        defillama=defillama,
        uniswapv2=uniswapv2_inquirer,
        uniswapv3=uniswapv3_inquirer,
    )
    historian.set_oracles_order(historical_price_oracles_order)
    maybe_mock_historical_price_queries(
        historian=historian,
        should_mock_price_queries=should_mock_price_queries,
        mocked_price_queries=mocked_price_queries,
        default_mock_value=default_mock_price_value,
        dont_mock_price_for=dont_mock_price_for,
        force_no_price_found_for=force_no_price_found_for,
    )

    return historian
