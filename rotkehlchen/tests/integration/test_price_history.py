import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.assets import A_BTC, A_EUR, A_USD
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.constants import A_DASH, A_XMR
from rotkehlchen.types import Price, Timestamp

HISTORICAL_PRICE_ORACLES = [
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
@pytest.mark.parametrize('historical_price_oracles_order', [HISTORICAL_PRICE_ORACLES])
@pytest.mark.vcr(filter_query_parameters=['api_key'])
def test_price_queries(price_historian, database):
    """Test some historical price queries. Make sure that we test some
    assets not in cryptocompare but in coingecko so the backup mechanism triggers and works"""

    # These should hit cryptocompare
    assert price_historian.query_historical_price(A_BTC, A_EUR, 1479200704) == FVal('664.837256889238')  # noqa: E501
    assert price_historian.query_historical_price(A_XMR, A_BTC, 1579200704) == FVal('0.00749129895207403')  # noqa: E501
    # this should hit the cryptocompare cache we are creating here
    cache_data = [HistoricalPrice(
        from_asset=A_DASH,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1438387200),
        price=Price(FVal('10')),
    ), HistoricalPrice(
        from_asset=A_DASH,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1438390800),
        price=Price(FVal('20')),
    )]
    GlobalDBHandler.add_historical_prices(cache_data)
    price_historian._PriceHistorian__instance._cryptocompare = Cryptocompare(database=database)
    price_historian.set_oracles_order(price_historian._oracles)
    assert price_historian.query_historical_price(A_DASH, A_USD, 1438387700) == FVal('10')
    # this should hit coingecko, since cornichon is not in cryptocompare
    expected_price = FVal('1.00036501912699')
    yusdt = EvmToken('eip155:1/erc20:0x2f08119C6f07c006695E079AAFc638b8789FAf18')
    assert price_historian.query_historical_price(yusdt, A_USD, 1704135600) == expected_price
