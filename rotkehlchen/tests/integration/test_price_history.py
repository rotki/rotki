import pytest

from rotkehlchen.constants.assets import A_BTC, A_CORN, A_EUR, A_USD
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.constants import A_DASH, A_XMR
from rotkehlchen.typing import Price, Timestamp


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_price_queries(price_historian, data_dir, database):
    """Test some historical price queries. Make sure that we test some
    assets not in cryptocompare but in coigecko so the backup mechanism triggers and works"""

    # These should hit cryptocompare
    assert price_historian.query_historical_price(A_BTC, A_EUR, 1479200704) == FVal('663.66')
    assert price_historian.query_historical_price(A_XMR, A_BTC, 1579200704) == FVal('0.007526')
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
    GlobalDBHandler().add_historical_prices(cache_data)
    price_historian._PriceHistorian__instance._cryptocompare = Cryptocompare(
        data_directory=data_dir,
        database=database,
    )
    price_historian.set_oracles_order(price_historian._oracles)
    assert price_historian.query_historical_price(A_DASH, A_USD, 1438387700) == FVal('10')
    # this should hit coingecko, since cornichon is not in cryptocompare
    expected_price = FVal('0.07830444726516915')
    assert price_historian.query_historical_price(A_CORN, A_USD, 1608854400) == expected_price
