from typing import TYPE_CHECKING, Any

import pytest

from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.externalapis.moralis import Moralis
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.tests.utils.history import maybe_mock_historical_price_queries
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.fixture(name='cryptocompare')
def fixture_cryptocompare(database: DBHandler) -> Cryptocompare:
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.CRYPTOCOMPARE,
                api_key=ApiKey('dummy-api-key'),
            )],
        )
    return Cryptocompare(database=database)


@pytest.fixture(scope='session', name='session_coingecko')
def fixture_session_coingecko() -> Coingecko:
    return Coingecko(database=None)


@pytest.fixture(name='coingecko')
def fixture_coingecko() -> Coingecko:
    return Coingecko(database=None)


@pytest.fixture(name='alchemy')
def fixture_alchemy(database: DBHandler) -> Alchemy:
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.ALCHEMY,
                api_key=ApiKey('dummy-api-key'),
            )],
        )
    return Alchemy(database=database)


@pytest.fixture(name='moralis')
def fixture_moralis(database: DBHandler) -> Moralis:
    with database.user_write() as write_cursor:
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.MORALIS,
                api_key=ApiKey('dummy-api-key'),
            )],
        )
    return Moralis(database=database)


@pytest.fixture(scope='session', name='session_defillama')
def fixture_session_defillama() -> Defillama:
    return Defillama(database=None)


@pytest.fixture(name='defillama')
def fixture_defillama() -> Defillama:
    return Defillama(database=None)


@pytest.fixture(name='uniswapv2_inquirer')
def fixture_uniswapv2() -> UniswapV2Oracle:
    return UniswapV2Oracle()


@pytest.fixture(name='uniswapv3_inquirer')
def fixture_uniswapv3() -> UniswapV3Oracle:
    return UniswapV3Oracle()


@pytest.fixture(name='historical_price_oracles_order')
def fixture_historical_price_oracles_order() -> tuple[HistoricalPriceOracle, ...]:
    return (
        HistoricalPriceOracle.COINGECKO,
        HistoricalPriceOracle.DEFILLAMA,
        HistoricalPriceOracle.UNISWAPV3,
        HistoricalPriceOracle.UNISWAPV2,
    )


@pytest.fixture(name='cryptocompare_historical_price_oracles_order')
def fixture_cryptocompare_historical_price_oracles_order() -> tuple[HistoricalPriceOracle, ...]:
    """CryptoCompare-first historical oracle order for VCR-cassette compatibility."""
    return (
        HistoricalPriceOracle.CRYPTOCOMPARE,
        HistoricalPriceOracle.COINGECKO,
        HistoricalPriceOracle.DEFILLAMA,
        HistoricalPriceOracle.UNISWAPV3,
        HistoricalPriceOracle.UNISWAPV2,
    )


@pytest.fixture(name='dont_mock_price_for')
def fixture_dont_mock_price_for() -> list[Any]:
    return []


@pytest.fixture(name='force_no_price_found_for')
def fixture_force_no_price_found_for() -> list[Any]:
    return []


@pytest.fixture
def price_historian(
        data_dir: Any,
        inquirer_defi: Any,  # pylint: disable=unused-argument
        should_mock_price_queries: bool,
        mocked_price_queries: Any,
        cryptocompare: Cryptocompare,
        coingecko: Coingecko,
        alchemy: Alchemy,
        moralis: Moralis,
        defillama: Defillama,
        uniswapv2_inquirer: UniswapV2Oracle,
        uniswapv3_inquirer: UniswapV3Oracle,
        default_mock_price_value: Any,
        historical_price_oracles_order: tuple[HistoricalPriceOracle, ...],
        dont_mock_price_for: list[Any],
        force_no_price_found_for: list[Any],
) -> PriceHistorian:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None  # type: ignore[attr-defined]
    historian = PriceHistorian(
        data_directory=data_dir,
        cryptocompare=cryptocompare,
        coingecko=coingecko,
        alchemy=alchemy,
        moralis=moralis,
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
