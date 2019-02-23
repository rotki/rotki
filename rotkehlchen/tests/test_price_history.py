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
    # 13/01/19 Cryptocompare fixed the error so our incosistency adjustment code that would
    # give the price of 8.945657222 is not hit.
    # 16/01/2019 They just reintroduced the error. So 9.0 is no longer returned
    assert eur_price.is_close(FVal('8.945657222'), max_diff=0.001)

    inv_usd_price = price_historian.query_historical_price('USD', 'DASH', 1479200704)
    assert inv_usd_price.is_close(FVal('0.103842'), max_diff=0.0001)
    inv_eur_price = price_historian.query_historical_price('EUR', 'DASH', 1479200704)
    # 13/01/19 Cryptocompare fixed the error so our incosistency adjustment code
    # that would give the price of 0.11179 is not hit
    # 16/01/2019 They just reintroduced the error. So 0.11115 is no longer returned
    assert inv_eur_price.is_close(FVal('0.11179'), max_diff=0.0001)


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
    do_queries_for('BTC', 'EUR', price_historian)
    do_queries_for('ETH', 'EUR', price_historian)


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_iota_query(price_historian):
    """
    Test that IOTA can be properly queried from cryptocompare

    Issue: https://github.com/rotkehlchenio/rotkehlchen/issues/299
    """
    usd_price = price_historian.query_historical_price('IOTA', 'USD', 1511793374)
    assert usd_price.is_close(FVal('0.954'))
    usd_price = price_historian.query_historical_price('IOT', 'USD', 1511793374)
    assert usd_price.is_close(FVal('0.954'))


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_bchsv_query(price_historian):
    """Test that BCHSV can be properly queried from cryptocompare (it's BSV there)"""
    btc_price = price_historian.query_historical_price('BCHSV', 'BTC', 1550945818)
    assert btc_price.is_close(FVal('0.01633'))
    btc_price = price_historian.query_historical_price('BSV', 'BTC', 1550945818)
    assert btc_price.is_close(FVal('0.01633'))
