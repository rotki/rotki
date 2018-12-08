from rotkehlchen.fval import FVal


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
    assert eur_price.is_close(FVal('8.945'), max_diff=0.001)

    inv_usd_price = price_historian.query_historical_price('USD', 'DASH', 1479200704)
    assert inv_usd_price.is_close(FVal('0.103842'), max_diff=0.0001)
    inv_eur_price = price_historian.query_historical_price('EUR', 'DASH', 1479200704)
    assert inv_eur_price.is_close(FVal('0.11179'), max_diff=0.0001)
