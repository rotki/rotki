import random

import pytest

from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import prices


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_incosistent_prices_double_checking(price_historian):
    """ This is a regression test for the incosistent DASH/EUR and DASH/USD prices
    that were returned on 02/12/2018. Issue:
    https://github.com/rotkehlchenio/rotkehlchen/issues/221
    """

    # Note the prices are not the same as in the issue because rotkehlchen uses
    # hourly rates while in the issue we showcased query of daily average
    usd_price = price_historian.query_historical_price('DASH', 'USD', 1479200704)
    assert usd_price.is_close(FVal('9.63'))
    eur_price = price_historian.query_historical_price('DASH', 'EUR', 1479200704)
    # Cryptocompare fixed the error so our incosistency adjustment code that would
    # give the price of 8.495 is not hit
    assert eur_price.is_close(FVal('9.0'), max_diff=0.001)

    inv_usd_price = price_historian.query_historical_price('USD', 'DASH', 1479200704)
    assert inv_usd_price.is_close(FVal('0.103842'), max_diff=0.0001)
    inv_eur_price = price_historian.query_historical_price('EUR', 'DASH', 1479200704)
    # Cryptocompare fixed the error so our incosistency adjustment code that would
    # give the price of 0.11179 is not hit
    assert inv_eur_price.is_close(FVal('0.11115'), max_diff=0.0001)


def do_queries_for(from_asset, to_asset, price_historian):
    queries = 5

    pair_map = prices[from_asset][to_asset]
    keys = random.sample(pair_map.keys(), min(queries, len(pair_map)))
    for timestamp in keys:
        price = price_historian.query_historical_price(from_asset, to_asset, timestamp)
        assert price.is_close(pair_map[timestamp])


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_price_queries(price_historian):
    """Test some cryptocompare price queries making sure our querying mechanism works"""
    # TODO: Get rid of the cache here and then try again with the cache
    do_queries_for('BTC', 'EUR', price_historian)
    do_queries_for('ETH', 'EUR', price_historian)
