import os
import warnings as test_warnings
from datetime import datetime
from typing import List
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import (
    A_BTC,
    A_CBAT,
    A_CDAI,
    A_CETH,
    A_CREP,
    A_CUSDC,
    A_CWBTC,
    A_CZRX,
    A_ETH,
    A_EUR,
    A_USD,
    A_USDT,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.externalapis.cryptocompare import (
    A_COMP,
    CRYPTOCOMPARE_HOURQUERYLIMIT,
    CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES,
    Cryptocompare,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.constants import A_DAO, A_SNGLS, A_XMR
from rotkehlchen.typing import Price, Timestamp


def test_cryptocompare_query_pricehistorical(cryptocompare):
    """Test that cryptocompare price historical query works fine"""
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=A_SNGLS,
        to_asset=A_BTC,
        timestamp=1475413990,
    )
    # Just test a price is returned
    assert price


def get_globaldb_cache_entries(from_asset: Asset, to_asset: Asset) -> List[HistoricalPrice]:
    """TODO: This should probaly be moved in the globaldb/handler.py if we use it elsewhere
    and made more generic (accept different sources)"""
    connection = GlobalDBHandler()._conn
    cursor = connection.cursor()
    query = cursor.execute(
        'SELECT from_asset, to_asset, source_type, timestamp, price FROM '
        'price_history WHERE from_asset=? AND to_asset=? AND source_type=? ORDER BY timestamp ASC',
        (
            from_asset.identifier,
            to_asset.identifier,
            HistoricalPriceOracle.CRYPTOCOMPARE.serialize_for_db(),  # pylint: disable=no-member
        ),
    )
    return [HistoricalPrice.deserialize_from_db(x) for x in query]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_historical_data_use_cached_price(data_dir, database, historical_price_test_data):  # pylint: disable=unused-argument  # noqa: E501
    """Test that the cryptocompare cache is used"""
    cc = Cryptocompare(data_directory=data_dir, database=database)
    with patch.object(cc, 'query_endpoint_histohour') as histohour_mock:
        result = cc.query_historical_price(
            from_asset=A_ETH,
            to_asset=A_EUR,
            timestamp=1511627623,
        )
        # make sure that histohour was not called, in essence that the cache was used
        assert histohour_mock.call_count == 0

    assert result == FVal(396.56)


def check_cc_result(result: List, forward: bool):
    for idx, entry in enumerate(result):
        if idx != 0:
            assert entry.timestamp == result[idx - 1].timestamp + 3600

        # For some reason there seems to be a discrepancy in the way results
        # are returned between the different queries. It's only minor but seems
        # like a cryptocompare issue
        change_ts_1 = 1287140400 if forward else 1287133200
        change_ts_2 = 1294340400 if forward else 1294333200

        if entry.timestamp <= change_ts_1:
            assert entry.price == Price(FVal('0.05454'))
        elif entry.timestamp <= change_ts_2:
            assert entry.price == Price(FVal('0.105'))
        elif entry.timestamp <= 1301544000:
            assert entry.price == Price(FVal('0.298'))
        else:
            raise AssertionError(f'Unexpected time entry {entry.time}')


@pytest.mark.freeze_time
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_histohour_data_going_forward(data_dir, database, freezer):
    """Test that the cryptocompare histohour data retrieval works properly

    This test checks that doing an additional query in the future works properly
    and appends the cached data with the newly returned data
    """
    # first timestamp cryptocompare has histohour BTC/USD when queried from this test is
    btc_start_ts = 1279940400
    now_ts = btc_start_ts + 3600 * 2000 + 122
    freezer.move_to(datetime.fromtimestamp(now_ts))
    cc = Cryptocompare(data_directory=data_dir, database=database)
    cc.query_and_store_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 2 - 55,
    )

    globaldb = GlobalDBHandler()
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT + 1
    assert all(x.price == Price(FVal(0.05454)) for x in result)
    data_range = globaldb.get_historical_price_range(A_BTC, A_USD, HistoricalPriceOracle.CRYPTOCOMPARE)  # noqa: E501
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1287140400  # that's the closest ts to now_ts cc returns

    # now let's move a bit to the future and query again to see the cache is appended to
    now_ts = now_ts + 3600 * 2000 * 2 + 4700
    freezer.move_to(datetime.fromtimestamp(now_ts))
    cc.query_and_store_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 4 - 55,
    )
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT * 3 + 2
    check_cc_result(result, forward=True)
    data_range = globaldb.get_historical_price_range(A_BTC, A_USD, HistoricalPriceOracle.CRYPTOCOMPARE)  # noqa: E501
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1301544000  # that's the closest ts to now_ts cc returns


@pytest.mark.freeze_time
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_histohour_data_going_backward(data_dir, database, freezer):
    """Test that the cryptocompare histohour data retrieval works properly

    This test checks that doing an additional query in the past workd properly
    and that the cached data are properly appended to the cached result. In production
    this scenario should not happen often. Only way to happen if cryptocompare somehow adds
    older data than what was previously queried.
    """
    globaldb = GlobalDBHandler()
    # first timestamp cryptocompare has histohour BTC/USD when queried from this test is
    btc_start_ts = 1279936800
    # first timestamp cryptocompare has histohour BTC/USD is: 1279940400
    now_ts = btc_start_ts + 3600 * 2000 + 122
    # create a cache file for BTC_USD
    cache_data = [HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1301536800),
        price=Price(FVal('0.298')),
    ), HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1301540400),
        price=Price(FVal('0.298')),
    )]
    globaldb.add_historical_prices(cache_data)

    freezer.move_to(datetime.fromtimestamp(now_ts))
    cc = Cryptocompare(data_directory=data_dir, database=database)
    cc.query_and_store_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 2 - 55,
    )
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT * 3 + 2
    check_cc_result(result, forward=False)
    data_range = globaldb.get_historical_price_range(A_BTC, A_USD, HistoricalPriceOracle.CRYPTOCOMPARE)  # noqa: E501
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1301540400  # that's the closest ts to now_ts cc returns


def test_cryptocompare_dao_query(cryptocompare):
    """
    Test that querying the DAO token for cryptocompare historical prices works. At some point
    it got accidentaly removed from cryptocompare. Then it got fixed.
    This test will show us if this happens again.

    Regression test for https://github.com/rotki/rotki/issues/548
    """
    price = cryptocompare.query_historical_price(
        from_asset=A_DAO,
        to_asset=A_USD,
        timestamp=1468886400,
    )
    assert price is not None


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in cryptocompare rate limiting. No need to run often',
)
@pytest.mark.parametrize('from_asset,to_asset,timestamp,price', [
    (A_ETH, A_USD, 1505527200, FVal('262.155')),
    (A_XMR, A_BTC, 1438992000, FVal('0.0026285')),
])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_historical_data_price(
        data_dir,
        database,
        from_asset,
        to_asset,
        timestamp,
        price,
):
    """Test that the cryptocompare histohour data retrieval works and price is returned

    """
    cc = Cryptocompare(data_directory=data_dir, database=database)
    # Get lots of historical prices from at least 1 query after the ts we need
    cc.query_and_store_historical_data(
        from_asset=from_asset,
        to_asset=to_asset,
        timestamp=timestamp + 2020 * 3600,
    )
    # Query the ts we need directly from the cached data
    price_cache_entry = GlobalDBHandler().get_historical_price(
        from_asset=from_asset,
        to_asset=to_asset,
        timestamp=timestamp,
        max_seconds_distance=3600,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )
    assert price_cache_entry.price == price


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would heavily contribute in cryptocompare rate limiting',
)
@pytest.mark.parametrize('run', (
    [{
        'asset': A_CDAI,
        'expected_price1': FVal('0.02008006'),
        'expected_price2': FVal('0.02033108'),
    }, {
        'asset': A_CBAT,
        'expected_price1': FVal('0.003809585'),
        'expected_price2': FVal('0.002713524'),
    }, {
        'asset': A_CETH,
        'expected_price1': FVal('2.901'),
        'expected_price2': FVal('2.669'),
    }, {
        'asset': A_CREP,
        'expected_price1': FVal('0.2046084'),
        'expected_price2': FVal('0.16380696'),
    }, {
        'asset': A_CUSDC,
        'expected_price1': FVal('0.02082156'),
        'expected_price2': FVal('0.020944869'),
    }, {
        'asset': A_CWBTC,
        'expected_price1': FVal('145.404910'),
        'expected_price2': FVal('99.411774'),
    }, {
        'asset': A_CZRX,
        'expected_price1': FVal('0.004415010'),
        'expected_price2': FVal('0.003037084'),
    }]),
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_query_compound_tokens(
        cryptocompare,
        price_historian,  # pylint: disable=unused-argument
        run,
):
    """
    Test that querying cryptocompare for compound tokens works for any target asset.

    This is due to a flaw in cryptocompare that compound tokens can only be queried
    against their non-compound counterpart.

    The test always uses a clean caching directory so requests are ALWAYS made to cryptocompare
    to test that everything works.
    """
    asset = run['asset']
    expected_price1 = run['expected_price1']
    expected_price2 = run['expected_price2']
    price = cryptocompare.query_historical_price(
        from_asset=asset,
        to_asset=A_USD,
        timestamp=1576195200,
    )
    assert price == expected_price1
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=asset,
        to_asset=A_USD,
        timestamp=1584662400,
    )
    assert price == expected_price2
    price = cryptocompare.query_current_price(
        from_asset=asset,
        to_asset=A_USD,
    )
    assert price is not None


@pytest.mark.parametrize('from_asset, to_asset, timestamp, expected_price', [
    (A_ETH, A_USD, Timestamp(1592629200), Price(ZERO)),
    (A_COMP, A_COMP, Timestamp(1592629200), Price(ZERO)),  # both assets COMP
    (A_USD, A_USD, Timestamp(1592629200), Price(ZERO)),  # both assets USD
    (A_COMP, A_USDT, Timestamp(1592629200), Price(ZERO)),  # to_asset USDT
    (A_USDT, A_COMP, Timestamp(1592629200), Price(ZERO)),  # from_asset USDT
    (A_COMP, A_USD, Timestamp(1592629200), Price(FVal('239.13'))),
    (A_USD, A_COMP, Timestamp(1592629200), Price(FVal('0.004181825785137791159620290219'))),
    (A_COMP, A_USD, Timestamp(1592629201), Price(ZERO)),  # timestamp gt
    (A_USD, A_COMP, Timestamp(1592629201), Price(ZERO)),  # timestamp gt
])
def test_check_and_get_special_histohour_price(
        cryptocompare,
        from_asset,
        to_asset,
        timestamp,
        expected_price,
):
    """
    Test expected prices are returned for different combinations of
    `from_asset`, `to_asset` and `timestamp`.
    """
    price = cryptocompare._check_and_get_special_histohour_price(
        from_asset=from_asset,
        to_asset=to_asset,
        timestamp=timestamp,
    )
    assert price == expected_price


def test_keep_special_histohour_cases_up_to_date(cryptocompare):
    """Test CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES assets timestamps are still
    valid by checking that for a smaller timestamp the response contains
    entries with all price attributes at zero.
    """
    def is_price_not_valid(hour_price_data):
        return all(hour_price_data[attr] == 0 for attr in ('low', 'high', 'open', 'close'))

    limit = 10
    for asset, asset_data in CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES.items():
        # Call `query_endpoint_histohour()` for handling special assets
        to_timestamp = Timestamp(asset_data.timestamp - 3600)
        from_timestamp = Timestamp(to_timestamp - limit * 3600)
        response = cryptocompare.query_endpoint_histohour(
            from_asset=asset,
            to_asset=A_USD,
            limit=limit,
            to_timestamp=to_timestamp,
        )
        if not any(is_price_not_valid(price_data) for price_data in response['Data']):
            warning_msg = (
                f'Cryptocompare histohour API has non-zero prices for asset '
                f'{asset.identifier} from {from_timestamp} to {to_timestamp}. '
                f' Please, update CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES dict '
                f'with a smaller timestamp.'
            )
            test_warnings.warn(UserWarning(warning_msg))


@pytest.mark.parametrize('include_cryptocompare_key', [True])
def test_cryptocompare_query_with_api_key(cryptocompare):
    """Just try to query cryptocompare endpoints with an api key

    Regression test for https://github.com/rotki/rotki/issues/2244
    """
    # call to an endpoint without any args
    response = cryptocompare._api_query('v2/news/')
    assert response and isinstance(response, list)
    # call to endpoint with args
    price = cryptocompare.query_current_price(A_ETH, A_USD)
    assert price is not None
