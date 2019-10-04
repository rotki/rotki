import random

import pytest

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_BSV, A_DASH, A_IOTA
from rotkehlchen.tests.utils.history import prices


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_inconsistent_prices_double_checking(price_historian):
    """ This is a regression test for the inconsistent DASH/EUR and DASH/USD prices
    that were returned on 02/12/2018. Issue:
    https://github.com/rotkehlchenio/rotkehlchen/issues/221
    """

    # Note the prices are not the same as in the issue because rotkehlchen uses
    # hourly rates while in the issue we showcased query of daily average
    usd_price = price_historian.query_historical_price(A_DASH, A_USD, 1479200704)
    assert usd_price.is_close(FVal('9.6125'))
    eur_price = price_historian.query_historical_price(A_DASH, A_EUR, 1479200704)
    assert eur_price.is_close(FVal('9.0015'), max_diff=0.001)

    inv_usd_price = price_historian.query_historical_price(A_USD, A_DASH, 1479200704)
    assert inv_usd_price.is_close(FVal('0.10385'), max_diff=0.0001)
    inv_eur_price = price_historian.query_historical_price(A_EUR, A_DASH, 1479200704)
    assert inv_eur_price.is_close(FVal('0.1111'), max_diff=0.0001)


def do_queries_for(from_asset, to_asset, price_historian):
    queries = 5

    pair_map = prices[from_asset][to_asset]
    keys = random.sample(pair_map.keys(), min(queries, len(pair_map)))
    for timestamp in keys:
        price = price_historian.query_historical_price(from_asset, to_asset, timestamp)
        msg = (
            f'Unexpected price for {from_asset} -> {to_asset} for {timestamp}. '
            f'Got {price} expected {pair_map[timestamp]}'
        )
        assert price.is_close(pair_map[timestamp]), msg

@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_price_queries(price_historian):
    """Test some cryptocompare price queries making sure our querying mechanism works"""
    # TODO: Get rid of the cache here and then try again with the cache
    # TODO2: Once historical price of DASH and other token stabilize perhaps also
    #        include them in the tests
    do_queries_for(A_BTC, A_EUR, price_historian)
    do_queries_for(A_ETH, A_EUR, price_historian)


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_iota_query(price_historian):
    """
    Test that IOTA can be properly queried from cryptocompare

    Issue: https://github.com/rotkehlchenio/rotkehlchen/issues/299
    """
    usd_price = price_historian.query_historical_price(A_IOTA, A_USD, 1511793374)
    assert usd_price.is_close(FVal('0.954'))


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_bchsv_query(price_historian):
    """Test that BCHSV can be properly queried from cryptocompare (it's BSV there)"""
    btc_price = price_historian.query_historical_price(A_BSV, A_BTC, 1550945818)
    assert btc_price.is_close(FVal('0.01633'))
