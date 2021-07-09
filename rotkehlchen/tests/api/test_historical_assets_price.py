import random

from http import HTTPStatus
import pytest
import requests

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
    assert_error_response,
    assert_simple_ok_response,
)


@pytest.mark.parametrize('mocked_price_queries', [{
    'BTC': {
        'USD': {
            1579543935: FVal('30000'),
            1611166335: FVal('35000'),
        },
    },
    'USD': {'USD': {1579543935: FVal('1')}},
    'GBP': {
        'USD': {
            1548007935: FVal('1.25'),
            1611166335: FVal('1.27'),
        },
    },
    'XRP': {'USD': {1611166335: FVal('0')}},
}])
def test_get_historical_assets_price(rotkehlchen_api_server):
    """Test given a list of asset-timestamp tuples it returns the asset price
    at the given timestamp.
    """
    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
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
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == {
        '1579543935': '30000',
        '1611166335': '35000',
    }
    assert result['assets']['USD'] == {'1579543935': '1'}
    assert result['assets']['GBP'] == {
        '1548007935': '1.25',
        '1611166335': '1.27',
    }
    assert result['assets']['XRP'] == {'1611166335': '0'}
    assert result['target_asset'] == 'USD'


def test_manual_historical_price(rotkehlchen_api_server, globaldb):
    curv = EthereumToken('0xD533a949740bb3306d119CC777fa900bA034cd52')
    curv_id = '_ceth_0xD533a949740bb3306d119CC777fa900bA034cd52'
    # First test adding assets
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': "1.20",
        },
    )
    assert_simple_ok_response(response)
    historical_price = globaldb.get_historical_price(
        from_asset=curv,
        to_asset=A_USD,
        timestamp=1611166335,
        max_seconds_distance=10,
    )
    assert historical_price.price == FVal(1.2)
    assert historical_price.from_asset == curv_id
    assert historical_price.to_asset == A_USD
    # Test with an unknown asset
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': '_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98621',
            'to_asset': 'USD',
            'timestamp': 1611166335,
            'price': "1.20",
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
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
            'to_asset': 'USD',
            'timestamp': 1611166340,
            'price': "1.30",
        },
    )
    # Try to edit entry
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
            'to_asset': 'USD',
            'timestamp': 1611166340,
            'price': "1.40",
        },
    )
    # Try to retrieve the assets price
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        params={
            'from_asset': curv_id,
        },
    )
    data = assert_proper_response_with_result(response)
    assert data[0]['from_asset'] == curv_id
    assert data[0]['to_asset'] == 'USD'
    assert data[0]['timestamp'] == 1611166335
    assert data[0]['price'] == '1.20'
    assert data[1]['from_asset'] == curv_id
    assert data[1]['to_asset'] == 'USD'
    assert data[1]['timestamp'] == 1611166340
    assert data[1]['price'] == '1.40'
    # If we query against the to_asset we should get the same entry
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        params={
            'to_asset': 'USD',
        },
    )
    data = assert_proper_response_with_result(response)
    assert len(data) == 2
    assert data[0]['from_asset'] == curv_id
    assert data[0]['to_asset'] == 'USD'
    assert data[0]['timestamp'] == 1611166335
    assert data[0]['price'] == '1.20'
    assert data[1]['from_asset'] == curv_id
    assert data[1]['to_asset'] == 'USD'
    assert data[1]['timestamp'] == 1611166340
    assert data[1]['price'] == '1.40'
    # Without the asset field should return all of them
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
    )
    data = assert_proper_response_with_result(response)
    assert len(data) == 2
    assert data[0]['from_asset'] == curv_id
    assert data[0]['to_asset'] == 'USD'
    assert data[0]['timestamp'] == 1611166335
    assert data[0]['price'] == '1.20'
    assert data[1]['from_asset'] == curv_id
    assert data[1]['to_asset'] == 'USD'
    assert data[1]['timestamp'] == 1611166340
    assert data[1]['price'] == '1.40'
    # Delete entry
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
            'to_asset': 'USD',
            'timestamp': 1611166335,
        },
    )
    # If we query again we should only see one result
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        params={
            'from_asset': curv_id,
        },
    )
    data = assert_proper_response_with_result(response)
    assert len(data) == 1
    assert data[0]['from_asset'] == curv_id
    assert data[0]['to_asset'] == 'USD'
    assert data[0]['timestamp'] == 1611166340
    assert data[0]['price'] == '1.40'
    # Delete an entry that is not in database
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
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
            "historicalassetspriceresource",
        ),
        json={
            'from_asset': curv_id,
            'to_asset': 'USD',
            'timestamp': 1611166344,
            'price': "1.40",
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to edit manual price',
        status_code=HTTPStatus.CONFLICT,
        result_exists=True,
    )
