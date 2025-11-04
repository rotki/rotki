import pytest

from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants.assets import (
    A_BAL,
    A_BTC,
    A_ETH,
    A_ETH_POL,
    A_POL,
    A_USD,
)
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
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


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_matic_pol_hardforked_price(price_historian: PriceHistorian):
    """Test that we return price of POL for MATIC after hardfork"""
    before_hardfork = Timestamp(POLYGON_POS_POL_HARDFORK - 1)
    after_hardfork = Timestamp(POLYGON_POS_POL_HARDFORK + 1)
    assert GlobalDBHandler.add_single_historical_price(HistoricalPrice(  # set MATIC price ZERO
        from_asset=A_POL,
        to_asset=A_USD,
        source=HistoricalPriceOracle.MANUAL,
        timestamp=before_hardfork,
        price=Price(ZERO),
    ))
    assert GlobalDBHandler.add_single_historical_price(HistoricalPrice(  # set POL price ONE
        from_asset=A_ETH_POL,
        to_asset=A_USD,
        source=HistoricalPriceOracle.MANUAL,
        timestamp=after_hardfork,
        price=Price(ONE),
    ))

    assert price_historian.query_historical_price(
        from_asset=A_POL,
        to_asset=A_USD,
        timestamp=before_hardfork,
    ) == Price(ZERO)  # MATIC price is ZERO
    assert price_historian.query_historical_price(
        from_asset=A_POL,  # query MATIC after hardfork
        to_asset=A_USD,
        timestamp=after_hardfork,
    ) == Price(ONE)  # POL price is ONE
