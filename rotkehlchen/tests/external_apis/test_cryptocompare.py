import datetime
import os

import pytest

from rotkehlchen.assets.asset import Asset, CryptoAsset
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_BTC,
    A_CBAT,
    A_CDAI,
    A_CETH,
    A_CREP,
    A_CUSDC,
    A_CWBTC,
    A_CZRX,
    A_DAI,
    A_DPI,
    A_ETH,
    A_EUR,
    A_USD,
)
from rotkehlchen.externalapis.cryptocompare import (
    CRYPTOCOMPARE_SPECIAL_CASES_MAPPING,
    Cryptocompare,
)
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.constants import A_SNGLS, A_XMR
from rotkehlchen.types import Price, Timestamp


def test_cryptocompare_query_pricehistorical(cryptocompare):
    """Test that cryptocompare price historical query works fine"""
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=A_SNGLS.resolve_to_asset_with_oracles(),
        to_asset=A_BTC.resolve_to_asset_with_oracles(),
        timestamp=1475413990,
    )
    # Just test a price is returned
    assert price


def get_globaldb_cache_entries(from_asset: Asset, to_asset: Asset) -> list[HistoricalPrice]:
    """TODO: This should probably be moved in the globaldb/handler.py if we use it elsewhere
    and made more generic (accept different sources)"""
    with GlobalDBHandler().conn.read_ctx() as cursor:
        query = cursor.execute(
            'SELECT from_asset, to_asset, source_type, timestamp, price FROM '
            'price_history WHERE from_asset=? AND to_asset=? AND source_type=? ORDER BY timestamp ASC',  # noqa: E501
            (
                from_asset.identifier,
                to_asset.identifier,
                HistoricalPriceOracle.CRYPTOCOMPARE.serialize_for_db(),  # pylint: disable=no-member
            ),
        )
        return [HistoricalPrice.deserialize_from_db(x) for x in query]


def check_cc_result(result: list, forward: bool):
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
def test_cryptocompare_histohour_data_going_forward(database, freezer):
    """Test that the cryptocompare histohour data retrieval works properly

    This test checks that doing an additional query in the future works properly
    and appends the cached data with the newly returned data
    """
    # first timestamp cryptocompare has histohour BTC/USD when queried from this test is
    btc_start_ts = 1279324800
    now_ts = btc_start_ts + 3600 * 24 * 100  # 100 days ahead
    freezer.move_to(datetime.datetime.fromtimestamp(now_ts, tz=datetime.UTC))
    cc = Cryptocompare(database=database)
    cc.query_and_store_historical_data(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
        timestamp=now_ts - 3600 * 2 - 55,
    )

    globaldb = GlobalDBHandler()
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) > 1000  # arbitrary safe number
    prices = [x.price for x in result]
    assert FVal('0.048') <= min(prices) <= FVal('0.049')
    assert FVal('0.185') <= max(prices) <= FVal('0.190')
    data_range = globaldb.get_historical_price_range(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1287964800  # that's the closest ts to now_ts cc returns
    old_cache_entries = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)

    # Move forward 14 days
    now_ts += 3600 * 24 * 14
    freezer.move_to(datetime.datetime.fromtimestamp(now_ts, tz=datetime.UTC))
    cc.query_and_store_historical_data(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
        timestamp=now_ts - 3600 * 4 - 55,
    )
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) > len(old_cache_entries)
    data_range = globaldb.get_historical_price_range(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1289174400  # that's the closest ts to now_ts cc returns


@pytest.mark.freeze_time
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_histohour_data_going_backward(database, freezer):
    """Test that the cryptocompare histohour data retrieval works properly

    This test checks that doing an additional query in the past worked properly
    and that the cached data are properly appended to the cached result. In production
    this scenario should not happen often. Only way to happen if cryptocompare somehow adds
    older data than what was previously queried.
    """
    globaldb = GlobalDBHandler()
    # first timestamp cryptocompare has histohour BTC/USD when queried from this test is
    btc_start_ts = 1279324800
    # first timestamp cryptocompare has histohour BTC/USD is: 1279324800
    now_ts = btc_start_ts + 3600 * 24 * 100  # 100 days ahead
    # create a cache file for BTC_USD
    cache_data = [HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1301536800),
        price=Price(FVal('0.800506052631579')),
    ), HistoricalPrice(
        from_asset=A_BTC,
        to_asset=A_USD,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
        timestamp=Timestamp(1301540400),
        price=Price(FVal('0.80098')),
    )]
    globaldb.add_historical_prices(cache_data)

    freezer.move_to(datetime.datetime.fromtimestamp(now_ts, tz=datetime.UTC))
    cc = Cryptocompare(database=database)
    cc.query_and_store_historical_data(
        from_asset=A_BTC.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
        timestamp=now_ts - 3600 * 2 - 55,
    )
    result = get_globaldb_cache_entries(from_asset=A_BTC, to_asset=A_USD)
    assert len(result) > 6000  # arbitrary safe number
    data_range = globaldb.get_historical_price_range(A_BTC, A_USD, HistoricalPriceOracle.CRYPTOCOMPARE)  # noqa: E501
    assert data_range[0] == btc_start_ts
    assert data_range[1] == 1301540400  # that's the closest ts to now_ts cc returns


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in cryptocompare rate limiting. No need to run often',
)
@pytest.mark.parametrize(('from_asset', 'to_asset', 'timestamp', 'price'), [
    (A_ETH, A_USD, 1505527200, FVal('262.155')),
    (A_XMR, A_BTC, 1438992000, FVal('0.0026285')),
])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_cryptocompare_historical_data_price(
        database,
        from_asset,
        to_asset,
        timestamp,
        price,
):
    """Test that the cryptocompare histohour data retrieval works and price is returned

    """
    cc = Cryptocompare(database=database)
    # Get lots of historical prices from at least 1 query after the ts we need
    cc.query_and_store_historical_data(
        from_asset=from_asset.resolve(),
        to_asset=to_asset.resolve(),
        timestamp=timestamp + 2020 * 3600,
    )
    # Query the ts we need directly from the cached data
    price_cache_entry = GlobalDBHandler().get_historical_price(
        from_asset=from_asset.resolve(),
        to_asset=to_asset.resolve(),
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
    usd = A_USD.resolve()
    asset = run['asset']
    expected_price1 = run['expected_price1']
    expected_price2 = run['expected_price2']
    price = cryptocompare.query_historical_price(
        from_asset=asset,
        to_asset=usd,
        timestamp=1576195200,
    )
    assert price == expected_price1
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=asset.resolve(),
        to_asset=usd,
        timestamp=1584662400,
    )
    assert price == expected_price2
    price, _ = cryptocompare.query_current_price(
        from_asset=asset.resolve(),
        to_asset=usd,
    )
    assert price is not None


@pytest.mark.skip('They are updating their systems & cleaning inactive pairs. Check again soon')
@pytest.mark.parametrize('include_cryptocompare_key', [True])
def test_cryptocompare_query_with_api_key(cryptocompare):
    """Just try to query cryptocompare endpoints with an api key

    Regression test for https://github.com/rotki/rotki/issues/2244
    """
    # call to an endpoint without any args
    response = cryptocompare._api_query('v2/news/')
    assert response and isinstance(response, list)
    # call to endpoint with args
    price, _ = cryptocompare.query_current_price(
        from_asset=A_ETH.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert price is not None
    # call to endpoint for a special asset to go into the special asset handling
    special_asset = A_CDAI
    assert special_asset in CRYPTOCOMPARE_SPECIAL_CASES_MAPPING
    price, _ = cryptocompare.query_current_price(
        from_asset=special_asset.resolve_to_asset_with_oracles(),
        to_asset=A_USD.resolve_to_asset_with_oracles(),
    )
    assert price is not None


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_starknet_historical_price_after_ticker_change(cryptocompare: 'Cryptocompare') -> None:
    """Check that Starknet token price query after Cryptocompare ticker change is accurate.

    It checks that price queries work properly after the May 9, 2024, switch
    from STARK to STRK ticker. Regression test for https://github.com/rotki/rotki/issues/8892
    """
    price = cryptocompare.query_endpoint_pricehistorical(
        from_asset=CryptoAsset('STRK'),
        to_asset=A_EUR.resolve_to_asset_with_oracles(),
        timestamp=Timestamp(1708510318),
    )
    assert price == Price(FVal('1.75404934188528'))


@pytest.mark.vcr
def test_special_cases(cryptocompare: 'Cryptocompare') -> None:
    a_eur, a_dpi = A_EUR.resolve_to_asset_with_oracles(), A_DPI.resolve_to_asset_with_oracles()
    current_price = cryptocompare._special_case_handling(
        method_name='query_current_price',
        from_asset=a_dpi,
        to_asset=a_eur,
    )
    historical_price = cryptocompare._special_case_handling(
        method_name='query_endpoint_pricehistorical',
        from_asset=a_dpi,
        to_asset=a_eur,
        timestamp=Timestamp(1732728240),
    )
    historical_data = cryptocompare._special_case_handling(
        method_name='query_endpoint_histohour',
        from_asset=a_dpi,
        to_asset=a_eur,
        limit=10,
        to_timestamp=Timestamp(1732728240),
    )

    assert current_price == FVal(325.97568)
    assert historical_price.is_close(FVal(116.3550477885))
    assert historical_data[0]['TIMESTAMP'] == 1732694400


@pytest.mark.vcr
def test_query_multiple_current_prices(cryptocompare: 'Cryptocompare'):
    assert cryptocompare.query_multiple_current_prices(
        from_assets=[
            A_BTC.resolve_to_asset_with_oracles(),
            A_DAI.resolve_to_asset_with_oracles(),
            A_BSC_BNB.resolve_to_asset_with_oracles(),
        ],
        to_asset=A_ETH.resolve_to_asset_with_oracles(),
    ) == {A_BTC: FVal(40.48), A_DAI: FVal(0.0004486), A_BSC_BNB: FVal(0.2673)}
