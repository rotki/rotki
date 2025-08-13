import random
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_CRV, A_ETH, A_USD
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.tests.fixtures.websockets import WebsocketReader


@pytest.mark.vcr
@pytest.mark.parametrize('legacy_messages_via_websockets', [True])
def test_get_historical_assets_price(
        rotkehlchen_api_server: APIServer,
        websocket_connection: 'WebsocketReader',
        legacy_messages_via_websockets: bool,  # pylint: disable=unused-argument
) -> None:
    """Test given a list of asset-timestamp tuples it returns the asset price
    at the given timestamp.
    """
    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'assets_timestamp': [
                ['BTC', 1579543935],
                ['BTC', 1611166335],
                ['USD', 1579543935],
                ['GBP', 1548007935],
                ['GBP', 1611166335],
                ['XRP', 1611166335],
            ],
            'target_asset': 'USD',
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert len(result) == 2
    assert result['assets']['BTC'] == {
        '1579543935': '8827.25596417741',
        '1611166335': '35538.1364151362',
    }
    assert result['assets']['USD'] == {'1579543935': '1'}
    assert result['assets']['GBP'] == {
        '1548007935': '1.287451',
        '1611166335': '1.365793',
    }
    assert result['assets']['XRP'] == {'1611166335': '0.295715040703119'}
    assert result['target_asset'] == 'USD'
    websocket_connection.wait_until_messages_num(num=3, timeout=2)
    for expected_processed_events in (0, 5, 6):
        assert websocket_connection.pop_message() == {
            'type': 'progress_updates',
            'data': {
                'total': 6,
                'processed': expected_processed_events,
                'subtype': 'multiple_prices_query_status',
            },
        }


@pytest.mark.freeze_time('2025-08-13 08:00:00 GMT')
def test_historical_assets_price_future_ts_error(
        rotkehlchen_api_server: APIServer,
) -> None:
    """Test error when setting or querying historical asset price with an invalid timestamp."""
    url = api_url_for(rotkehlchen_api_server, 'historicalassetspriceresource')
    for request_fnc, json in (
        (requests.put, {'from_asset': 'ETH', 'to_asset': 'USD', 'price': '1234', 'timestamp': 10000000000}),  # noqa: E501
        (requests.post, {'assets_timestamp': [['BTC', 10000000000]], 'target_asset': 'USD'}),
    ):
        assert_error_response(
            response=request_fnc(url=url, json=json),
            contained_in_msg='Given date cannot be in the future',
            status_code=HTTPStatus.BAD_REQUEST,
        )


def _assert_expected_prices(
        data: list[dict[str, Any]],
        after_deletion: bool,
        crv_1611166340_price: str = '1.40',
) -> None:
    assert len(data) == 2 if after_deletion else 3

    expected_data = []
    if after_deletion is False:
        expected_data.append({
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': '1.20',
        })

    expected_data.extend([{
        'from_asset': A_CRV.identifier,
        'to_asset': 'USD',
        'timestamp': 1611166340,
        'price': crv_1611166340_price,
    }, {
        'from_asset': A_CRV.identifier,
        'to_asset': 'USD',
        'timestamp': 1631166335,
        'price': '0',
    }])
    assert data == expected_data


def test_manual_historical_price(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
    ) -> None:
    # Test normal price
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': '1.20',
        },
    )
    assert_simple_ok_response(response)
    historical_price = globaldb.get_historical_price(
        from_asset=A_CRV,
        to_asset=A_USD,
        timestamp=Timestamp(1611166335),
        max_seconds_distance=10,
    )
    assert historical_price is not None
    assert historical_price.price == FVal(1.2)
    assert historical_price.from_asset == A_CRV.identifier
    assert historical_price.to_asset == A_USD
    # Test with zero price
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1631166335,
            'price': '0',
        },
    )
    assert_simple_ok_response(response)
    historical_price = globaldb.get_historical_price(
        from_asset=A_CRV,
        to_asset=A_USD,
        timestamp=Timestamp(1631166335),
        max_seconds_distance=10,
    )
    assert historical_price is not None
    assert historical_price.price == ZERO
    assert historical_price.from_asset == A_CRV.identifier
    assert historical_price.to_asset == A_USD

    # Test negative price fails properly
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': '-1.20',
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='A negative price is not allowed',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Test unknown asset fails properly
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': '_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98621',
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': '1.20',
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Add another entry for curve at a different timestamp
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166340,
            'price': '1.30',
        },
    )
    # Try to edit entry
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166340,
            'price': '1.50',
        },
    )
    # Try to retrieve the assets price
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        params={
            'from_asset': A_CRV.identifier,
        },
    )
    data = assert_proper_sync_response_with_result(response)
    _assert_expected_prices(data, after_deletion=False, crv_1611166340_price='1.50')
    # Check that calling PUT for an existing price replaces the price
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166340,
            'price': '1.40',
        },
    )
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        params={
            'from_asset': A_CRV.identifier,
        },
    )
    data = assert_proper_sync_response_with_result(response)
    _assert_expected_prices(data, after_deletion=False)
    # If we query against the to_asset we should get the same entry
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        params={
            'to_asset': 'USD',
        },
    )
    _assert_expected_prices(data, after_deletion=False)
    # Without the asset field should return all of them
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
    )
    data = assert_proper_sync_response_with_result(response)
    _assert_expected_prices(data, after_deletion=False)
    # Delete entry
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166335,
        },
    )
    # If we query again we should only see two results
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        params={
            'from_asset': A_CRV.identifier,
        },
    )
    data = assert_proper_sync_response_with_result(response)
    _assert_expected_prices(data, after_deletion=True)
    # Delete an entry that is not in database
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166338,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to delete manual price',
        status_code=HTTPStatus.CONFLICT,
        result_exists=True,
    )
    # Try to edit an entry that doesn't exists
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'from_asset': A_CRV.identifier,
            'to_asset': 'USD',
            'timestamp': 1611166344,
            'price': '1.40',
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to edit manual price',
        status_code=HTTPStatus.CONFLICT,
        result_exists=True,
    )


def test_historical_price_cache_only(
        rotkehlchen_api_server: APIServer,
        globaldb: GlobalDBHandler,
) -> None:
    """Test querying only cached historical prices with different cache periods

    Test that:
    1. With only_cache_period we get only cached prices that fall within +/- cache_period
       of the queried timestamp
    2. Missing prices are not shown in the response
    3. Invalid cache period fails properly
    """
    globaldb.add_historical_prices(entries=[
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1579543935),
            price=Price(FVal('30000')),
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        ),
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1579543935 + 2000),
            price=Price(FVal('31000')),
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        ),
        HistoricalPrice(
            from_asset=A_ETH,
            to_asset=A_USD,
            timestamp=Timestamp(1579543935),
            price=Price(FVal('1400')),
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        ),
        HistoricalPrice(
            from_asset=A_GBP,
            to_asset=A_USD,
            timestamp=Timestamp(1579543935),
            price=ZERO_PRICE,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
        ),
    ])

    # Test 1: Query with 1000-second cache period
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'historicalassetspriceresource',
        ),
        json={
            'assets_timestamp': [
                ['BTC', 1579543935],  # exact match with first entry
                ['BTC', 1579544435],  # 500s after first entry
                ['BTC', 1579545935],  # 2000s after first entry
                ['BTC', 1579544935],  # 1000s after first entry
                ['BTC', 1579543435],  # 500s before first entry
                ['BTC', 1579542935],  # 1000s before first entry
                ['BTC', 1579542435],  # 1500s before first entry
                ['ETH', 1579543935],  # exact match
                ['XRP', 1579543935],  # no data in DB, no data is returned
                ['GBP', 1579543935],  # exact match
            ],
            'target_asset': 'USD',
            'only_cache_period': 1000,  # +/- 1000 seconds range
        },
    )

    result = assert_proper_sync_response_with_result(response)
    assert result['assets']['BTC'] == {
        '1579543935': '30000',  # exact match first entry
        '1579544435': '30000',  # within range of first entry
        '1579545935': '31000',  # exact match second entry
        '1579544935': '30000',  # at edge of first entry's range
        '1579543435': '30000',  # within range of first entry
        '1579542935': '30000',  # at edge of first entry's range
    }
    assert result['assets']['ETH'] == {'1579543935': '1400'}  # exact match
    assert result['assets']['GBP'] == {'1579543935': '0'}  # exact match
    assert result['target_asset'] == 'USD'

    # Test 3: Test invalid cache period & zero cache
    for i in [-1, 0]:
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'historicalassetspriceresource',
            ),
            json={
                'assets_timestamp': [['BTC', 1579543935]],
                'target_asset': 'USD',
                'only_cache_period': i,  # negative period or zero value
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg='Cache period must be a positive integer',
            status_code=HTTPStatus.BAD_REQUEST,
        )
