import os
import warnings as test_warnings
from datetime import datetime
from typing import List
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD, A_USDT
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp
from rotkehlchen.externalapis.cryptocompare import (
    A_COMP,
    CRYPTOCOMPARE_HOURQUERYLIMIT,
    CRYPTOCOMPARE_SPECIAL_HISTOHOUR_CASES,
    PRICE_HISTORY_FILE_PREFIX,
    Cryptocompare,
    PairCacheKey,
)
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_SNGLS, A_XMR
from rotkehlchen.typing import Price, Timestamp
from rotkehlchen.utils.misc import get_or_make_price_history_dir


def test_cryptocompare_query_pricehistorical(cryptocompare):
    """Test that cryptocompare price historical query works fine"""
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=A_SNGLS,
        to_asset=A_BTC,
        timestamp=1475413990,
    )
    # Just test a price is returned
    assert price


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_historical_data_use_cached_price(data_dir, database):
    """Test that the cryptocompare cache is used and also properly deserialized"""
    # Create a cache file for SNGLS_BTC
    contents = """{"start_time": 0, "end_time": 1439390800,
    "data": [{"time": 1438387200, "close": 10, "high": 10, "low": 10, "open": 10,
    "volumefrom": 10, "volumeto": 10}, {"time": 1438390800, "close": 20, "high": 20,
    "low": 20, "open": 20, "volumefrom": 20, "volumeto": 20}]}"""
    price_history_dir = get_or_make_price_history_dir(data_dir)
    with open(price_history_dir / f'{PRICE_HISTORY_FILE_PREFIX}SNGLS_BTC.json', 'w') as f:
        f.write(contents)

    cc = Cryptocompare(data_directory=data_dir, database=database)
    with patch.object(cc, 'query_endpoint_histohour') as histohour_mock:
        result = cc.get_historical_data(
            from_asset=A_SNGLS,
            to_asset=A_BTC,
            timestamp=1438390801,
            only_check_cache=False,
        )
        # make sure that histohour was not called, in essence that the cache was used
        assert histohour_mock.call_count == 0

    assert len(result) == 2
    assert isinstance(result[0].low, FVal)
    assert result[0].low == FVal(10)
    assert isinstance(result[0].high, FVal)
    assert result[0].high == FVal(10)
    assert isinstance(result[1].low, FVal)
    assert result[1].low == FVal(20)
    assert isinstance(result[1].high, FVal)
    assert result[1].high == FVal(20)


def check_cc_result(query_result: List, forward: bool):
    for idx, entry in enumerate(query_result):
        if idx != 0:
            assert entry.time == query_result[idx - 1].time + 3600

        # For some reason there seems to be a discrepancy in the way results
        # are returned between the different queries. It's only minor but seems
        # like a cryptocompare issue
        change_ts_1 = 1287140400 if forward else 1287133200
        change_ts_2 = 1294340400 if forward else 1294333200

        if entry.time <= change_ts_1:
            assert entry.low == entry.high == FVal('0.05454')
        elif entry.time <= change_ts_2:
            assert entry.low == entry.high == FVal('0.105')
        elif entry.time <= 1301544000:
            assert entry.low == entry.high == FVal('0.298')
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
    result = cc.get_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 2 - 55,
        only_check_cache=False,
    )
    cache_key = PairCacheKey('BTC_USD')
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT + 1
    assert all(x.low == x.high == FVal('0.05454') for x in result)
    assert cache_key in cc.price_history
    assert cc.price_history[cache_key].start_time == btc_start_ts
    assert cc.price_history[cache_key].end_time == now_ts
    assert all(x.low == x.high == FVal('0.05454') for x in cc.price_history[cache_key].data)

    # now let's move a bit to the future and query again to see the cache is appended to
    now_ts = now_ts + 3600 * 2000 * 2 + 4700
    freezer.move_to(datetime.fromtimestamp(now_ts))
    result = cc.get_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 4 - 55,
        only_check_cache=False,
    )
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT * 3 + 2
    check_cc_result(result, forward=True)
    assert cache_key in cc.price_history
    assert cc.price_history[cache_key].start_time == btc_start_ts
    assert cc.price_history[cache_key].end_time == now_ts
    check_cc_result(cc.price_history[cache_key].data, forward=True)


@pytest.mark.freeze_time
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_histohour_data_going_backward(data_dir, database, freezer):
    """Test that the cryptocompare histohour data retrieval works properly

    This test checks that doing an additional query in the past workd properly
    and that the cached data are properly appended to the cached result. In production
    this scenario should not happen often. Only way to happen if cryptocompare somehow adds
    older data than what was previously queried.
    """
    # first timestamp cryptocompare has histohour BTC/USD when queried from this test is
    btc_start_ts = 1279936800
    # first timestamp cryptocompare has histohour BTC/USD is: 1279940400
    now_ts = btc_start_ts + 3600 * 2000 + 122
    # create a cache file for BTC_USD
    contents = """{"start_time": 1301536800, "end_time": 1301540400,
    "data": [{"time": 1301536800, "close": 0.298, "high": 0.298, "low": 0.298, "open": 0.298,
    "volumefrom": 0.298, "volumeto": 0.298}, {"time": 1301540400, "close": 0.298, "high": 0.298,
    "low": 0.298, "open": 0.298, "volumefrom": 0.298, "volumeto": 0.298}]}"""
    price_history_dir = get_or_make_price_history_dir(data_dir)
    with open(price_history_dir / f'{PRICE_HISTORY_FILE_PREFIX}BTC_USD.json', 'w') as f:
        f.write(contents)
    freezer.move_to(datetime.fromtimestamp(now_ts))
    cc = Cryptocompare(data_directory=data_dir, database=database)
    result = cc.get_historical_data(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=now_ts - 3600 * 2 - 55,
        only_check_cache=False,
    )
    cache_key = PairCacheKey('BTC_USD')
    assert len(result) == CRYPTOCOMPARE_HOURQUERYLIMIT * 3 + 2
    check_cc_result(result, forward=False)
    assert cache_key in cc.price_history
    assert cc.price_history[cache_key].start_time == btc_start_ts
    assert cc.price_history[cache_key].end_time == now_ts
    check_cc_result(cc.price_history[cache_key].data, forward=False)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_empty_histohour(data_dir, database, freezer):
    """Histohour can be empty and can have also floating point zeros like in CHI/EUR

    This test makes sure that an empty list is returned at the very first all zeros
    result that also has floating point and querying stops.

    If cryptocompare actually fixes their zero historical price problem this test can go away
    """
    now_ts = 1610365553
    freezer.move_to(datetime.fromtimestamp(now_ts))
    cc = Cryptocompare(data_directory=data_dir, database=database)
    result = cc.get_historical_data(
        from_asset=Asset('CHI'),
        to_asset=Asset('EUR'),
        timestamp=now_ts,
        only_check_cache=False,
    )
    assert len(result) == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_cryptocompare_histohour_query_old_ts_xcp(
        cryptocompare,
        price_historian,  # pylint: disable=unused-argument
):
    """Test that as a result of this query a crash does not happen.

    Regression for: https://github.com/rotki/rotki/issues/432
    Unfortunately still no price is found so we have to expect a NoPriceForGivenTimestamp

    This test is now skipped since it's a subset of:
    test_end_to_end_tax_report::test_cryptocompare_asset_and_price_not_found_in_history_processing

    When more price data sources are introduced then this should probably be unskipped
    to focus on the cryptocompare case. But at the moment both tests follow the same
    path and are probably slow due to the price querying.
    """
    with pytest.raises(NoPriceForGivenTimestamp):
        cryptocompare.query_historical_price(
            from_asset=Asset('XCP'),
            to_asset=A_USD,
            timestamp=1392685761,
        )


def test_cryptocompare_dao_query(cryptocompare):
    """
    Test that querying the DAO token for cryptocompare historical prices works. At some point
    it got accidentaly removed from cryptocompare. Then it got fixed.
    This test will show us if this happens again.

    Regression test for https://github.com/rotki/rotki/issues/548
    """
    price = cryptocompare.query_historical_price(
        from_asset=Asset('DAO'),
        to_asset=A_USD,
        timestamp=1468886400,
    )
    assert price is not None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_get_cached_data_metadata(data_dir, database):
    """Test that the get_cached_data_metadata function works correctly
    and returns just the metadata by reading part ofthe file

    The json cache data in production are saved as one line files.
    So here we also keep it in one line on purpose. The previous
    regex we used failed with 1 line json file
    """
    contents = """{"start_time": 1301536800, "end_time": 1301540400, "data": [{"time": 1301536800, "close": 0.298, "high": 0.298, "low": 0.298, "open": 0.298, "volumefrom": 0.298, "volumeto": 0.298}, {"time": 1301540400, "close": 0.298, "high": 0.298, "low": 0.298, "open": 0.298, "volumefrom": 0.298, "volumeto": 0.298}]}"""  # noqa: E501
    price_history_dir = get_or_make_price_history_dir(data_dir)
    with open(price_history_dir / f'{PRICE_HISTORY_FILE_PREFIX}BTC_USD.json', 'w') as f:
        f.write(contents)
    cc = Cryptocompare(data_directory=data_dir, database=database)
    # make sure that _read_cachefile_metadata runs and they are read from file and not from memory
    cc.price_history = {}
    result = cc.get_cached_data_metadata(
        from_asset=A_BTC,
        to_asset=A_USD,
    )
    assert result is not None
    assert result[0] == 1301536800
    assert result[1] == 1301540400


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
    result = cc.get_historical_data(
        from_asset=from_asset,
        to_asset=to_asset,
        timestamp=timestamp + 2020 * 3600,
        only_check_cache=False,
    )
    # Query the ts we need from the cached data
    result_price = cc._retrieve_price_from_data(
        data=result,
        from_asset=from_asset,
        to_asset=to_asset,
        timestamp=timestamp,
    )
    assert result_price == price


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would heavily contribute in cryptocompare rate limiting',
)
@pytest.mark.parametrize('run', (
    [{
        'asset': Asset('cDAI'),
        'expected_price1': FVal('0.02008006'),
        'expected_price2': FVal('0.02033108'),
    }, {
        'asset': Asset('cBAT'),
        'expected_price1': FVal('0.003809585'),
        'expected_price2': FVal('0.002713524'),
    }, {
        'asset': Asset('cETH'),
        'expected_price1': FVal('2.901'),
        'expected_price2': FVal('2.669'),
    }, {
        'asset': Asset('cREP'),
        'expected_price1': FVal('0.2046084'),
        'expected_price2': FVal('0.16380696'),
    }, {
        'asset': Asset('cUSDC'),
        'expected_price1': FVal('0.02082156'),
        'expected_price2': FVal('0.020944869'),
    }, {
        'asset': Asset('cWBTC'),
        'expected_price1': FVal('145.404910'),
        'expected_price2': FVal('99.411774'),
    }, {
        'asset': Asset('cZRX'),
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
