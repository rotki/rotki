from http import HTTPStatus

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.typing import AssetType, Location


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_adding_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for adding a custom asset works"""

    custom1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom1_id)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == custom1['name']
    assert data.symbol == custom1['symbol']
    assert data.started == custom1['started']

    custom2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'goo-token',
        'cryptocompare': 'GOO',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom2,
    )
    result = assert_proper_response_with_result(response)
    custom2_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom2_id)
    assert data.identifier == custom2_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == custom2['name']
    assert data.symbol == custom2['symbol']
    assert data.started == custom2['started']
    assert data.forked == custom2['forked']
    assert data.swapped_for == custom2['swapped_for']
    assert data.coingecko == custom2['coingecko']
    assert data.cryptocompare == custom2['cryptocompare']

    # try to add a token type/name/symbol combo that exists
    bad_asset = {
        'asset_type': 'fiat',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Failed to add fiat Euro since it already exists. Existing ids: EUR'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # try to add an ethereum token with the custom asset endpoint
    bad_asset = {
        'asset_type': 'ethereum token',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Asset type ethereum token is not allowed in this endpoint'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to add non existing forked and swapped for
    bad_asset = {
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'forked': 'dsadsadsadasd',
        'swapped_for': 'asdsadsad',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Unknown asset'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_editing_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for editing a custom asset works"""

    custom1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    data = globaldb.get_asset_data(identifier=custom1_id)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.OWN_CHAIN
    assert data.name == custom1['name']
    assert data.symbol == custom1['symbol']
    assert data.started == custom1['started']

    custom1_v2 = {
        'identifier': custom1_id,
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'goo-token',
        'cryptocompare': 'GOO',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1_v2,
    )
    result = assert_proper_response_with_result(response)
    assert result is True

    data = globaldb.get_asset_data(identifier=custom1_id)
    assert data.identifier == custom1_id
    assert data.asset_type == AssetType.STELLAR_TOKEN
    assert data.name == custom1_v2['name']
    assert data.symbol == custom1_v2['symbol']
    assert data.started == custom1_v2['started']
    assert data.forked == custom1_v2['forked']
    assert data.swapped_for == custom1_v2['swapped_for']
    assert data.coingecko == custom1_v2['coingecko']
    assert data.cryptocompare == custom1_v2['cryptocompare']

    # try to edit an asset with a non-existing identifier
    bad_asset = {
        'identifier': 'notexisting',
        'asset_type': 'own chain',
        'name': 'Euro',
        'symbol': 'EUR',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Tried to edit non existing asset with identifier notexisting'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )
    # try to edit an ethereum token with the custom asset endpoint
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'ethereum token',
        'name': 'ethereum Euro',
        'symbol': 'EUR',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Asset type ethereum token is not allowed in this endpoint'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # try to edit non existing forked and swapped for
    bad_asset = {
        'identifier': 'EUR',
        'asset_type': 'omni token',
        'name': 'Euro',
        'symbol': 'EUR',
        'forked': 'dsadsadsadasd',
        'swapped_for': 'asdsadsad',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=bad_asset,
    )
    expected_msg = 'Unknown asset'
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_deleting_custom_assets(rotkehlchen_api_server, globaldb):
    """Test that the endpoint for deleting a custom asset works"""

    custom1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']

    custom2 = {
        'asset_type': 'stellar token',
        'name': 'goo token',
        'symbol': 'GOO',
        'started': 6,
        'forked': custom1_id,
        'swapped_for': 'ETH',
        'coingecko': 'goo-token',
        'cryptocompare': 'GOO',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom2,
    )
    result = assert_proper_response_with_result(response)
    custom2_id = result['identifier']

    custom3 = {
        'asset_type': 'own chain',
        'name': 'boo token',
        'symbol': 'BOO',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom3,
    )
    result = assert_proper_response_with_result(response)
    custom3_id = result['identifier']

    # Delete custom 3 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom3_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom3_id) is None

    # Try to delete custom1 but make sure it fails. It's used by custom2
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
    )
    expected_msg = 'Tried to delete asset with name "foo token" and symbol "FOO" but its deletion would violate a constraint so deletion failed'  # noqa: E501
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )

    # Delete custom 2 and assert it works
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom2_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom2_id) is None

    # now custom 1 should be deletable
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    assert globaldb.get_asset_data(identifier=custom1_id) is None

    # Make sure that deleting unknown asset is detected
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': 'notexisting'},
    )
    expected_msg = 'Tried to delete asset with identifier notexisting but it was not found in the DB'  # noqa: E501
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [True])
def test_custom_asset_delete_guard(rotkehlchen_api_server):
    """Test that deleting an owned asset is guarded against"""
    user_db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    custom1 = {
        'asset_type': 'own chain',
        'name': 'foo token',
        'symbol': 'FOO',
        'started': 5,
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json=custom1,
    )
    result = assert_proper_response_with_result(response)
    custom1_id = result['identifier']
    user_db.add_manually_tracked_balances([ManuallyTrackedBalance(
        asset=Asset(custom1_id),
        label='manual1',
        amount=FVal(1),
        location=Location.EXTERNAL,
        tags=None,
    )])
    # Try to delete the asset and see it fails because a user owns it
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'allassetsresource',
        ),
        json={'identifier': custom1_id},
    )
    expected_msg = (
        'Tried to delete asset with name "foo token" and symbol "FOO" but its deletion '
        'would violate a constraint'
    )
    assert_error_response(
        response=response,
        contained_in_msg=expected_msg,
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_logged_in_user', [False])
def test_query_asset_types(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'assetstypesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result == [str(x) for x in AssetType]
    assert all(isinstance(AssetType.deserialize(x), AssetType) for x in result)
