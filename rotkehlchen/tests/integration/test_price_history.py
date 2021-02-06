import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.externalapis.cryptocompare import PRICE_HISTORY_FILE_PREFIX, Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_DASH, A_EUR, A_XMR
from rotkehlchen.utils.misc import get_or_make_price_history_dir


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_price_queries(price_historian, data_dir, database):
    """Test some historical price queries. Make sure that we test some
    assets not in cryptocompare but in coigecko so the backup mechanism triggers and works"""

    # These should hit cryptocompare
    assert price_historian.query_historical_price(A_BTC, A_EUR, 1479200704) == FVal('663.66')
    assert price_historian.query_historical_price(A_XMR, A_BTC, 1579200704) == FVal('0.007526')
    # this should hit the cryptocompare cache we are creating here
    contents = """{"start_time": 0, "end_time": 1439390800,
    "data": [{"time": 1438387200, "close": 10, "high": 10, "low": 10, "open": 10,
    "volumefrom": 10, "volumeto": 10}, {"time": 1438390800, "close": 20, "high": 20,
    "low": 20, "open": 20, "volumefrom": 20, "volumeto": 20}]}"""
    price_history_dir = get_or_make_price_history_dir(data_dir)
    with open(price_history_dir / f'{PRICE_HISTORY_FILE_PREFIX}DASH_USD.json', 'w') as f:
        f.write(contents)
    price_historian._PriceHistorian__instance._cryptocompare = Cryptocompare(
        data_directory=data_dir,
        database=database,
    )
    price_historian.set_oracles_order(price_historian._oracles)
    assert price_historian.query_historical_price(A_DASH, A_USD, 1438387700) == FVal('10')
    # this should hit coingecko, since cornichon is not in cryptocompare
    cornichon = Asset('CORN-2')
    expected_price = FVal('0.07830444726516915')
    assert price_historian.query_historical_price(cornichon, A_USD, 1608854400) == expected_price
