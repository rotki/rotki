from rotkehlchen.constants.assets import A_BAL, A_BTC, A_ETH, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.constants import A_EUR
from rotkehlchen.types import Price, Timestamp


def test_get_historical_price_range(globaldb, historical_price_test_data):  # pylint: disable=unused-argument
    assert globaldb.get_historical_price_range(
        from_asset=A_ETH,
        to_asset=A_EUR,
    ) == (Timestamp(1439048640), Timestamp(1618481196))
    assert globaldb.get_historical_price_range(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    ) == (Timestamp(1439048640), Timestamp(1539713117))
    assert globaldb.get_historical_price_range(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
    ) == (Timestamp(1511626622), Timestamp(1618481196))
    assert globaldb.get_historical_price_range(
        from_asset=A_BTC,
        to_asset=A_EUR,
    ) == (Timestamp(1428994442), Timestamp(1618481102))

    # Also test that price not found returns None
    assert globaldb.get_historical_price_range(
        from_asset=A_BAL,
        to_asset=A_EUR,
    ) is None
    assert globaldb.get_historical_price_range(
        from_asset=A_ETH,
        to_asset=A_USD,
    ) is None
    assert globaldb.get_historical_price_range(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.MANUAL,
    ) is None


def test_get_historical_price_data(globaldb, historical_price_test_data):  # pylint: disable=unused-argument
    data = globaldb.get_historical_price_data(source=HistoricalPriceOracle.CRYPTOCOMPARE)
    assert data == [{
        'from_asset': 'BTC',
        'to_asset': 'EUR',
        'from_timestamp': 1428994442,
        'to_timestamp': 1539713117,
    }, {
        'from_asset': 'ETH',
        'to_asset': 'EUR',
        'from_timestamp': 1439048640,
        'to_timestamp': 1539713117,
    }]


def test_get_historical_price(globaldb, historical_price_test_data):  # pylint: disable=unused-argument
    # test normal operation, multiple arguments
    expected_entry = HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1511626623),
        price=Price(FVal(396.56)),
    )
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1511627623,
        max_seconds_distance=3600,
    )
    assert expected_entry == price_entry
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1511627623,
        max_seconds_distance=3600,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )
    assert expected_entry == price_entry
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1511627623,
        max_seconds_distance=3600,
        source=HistoricalPriceOracle.MANUAL,
    )
    assert price_entry is None

    # nothing in a small distance
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1511627623,
        max_seconds_distance=10,
    )
    assert price_entry is None

    # multiple possible entries, make sure closest is returned
    expected_entry = HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        source=HistoricalPriceOracle.COINGECKO,
        timestamp=Timestamp(1618481101),
        price=Price(FVal(2049.76)),
    )
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1618481099,
        max_seconds_distance=3600,
    )
    assert expected_entry == price_entry

    # missing from asset
    price_entry = globaldb.get_historical_price(
        from_asset=A_BAL,
        to_asset=A_EUR,
        timestamp=1618481099,
        max_seconds_distance=3600,
    )
    assert price_entry is None

    # missing to asset
    price_entry = globaldb.get_historical_price(
        from_asset=A_ETH,
        to_asset=A_USD,
        timestamp=1618481099,
        max_seconds_distance=3600,
    )
    assert price_entry is None
