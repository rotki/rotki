from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import requests

from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BINANCEUS,
    LOCATION_COINBASE,
    LOCATION_COINBASEPRIME,
    LOCATION_COINBASEPRO,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

NUM_PACKAGED_ASSETS_MAPPINGS: Final = 3943


def _get_all_connector_mappings(rotkehlchen_api_server: APIServer) -> Any:
    """Utility function to return all the connector asset mappings in the DB."""
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
    )
    return assert_proper_sync_response_with_result(response=response)


def test_connector_asset_mappings_query(rotkehlchen_api_server: APIServer) -> None:
    """Test the connector asset mappings API for querying the mappings."""
    # query all the mappings
    result = _get_all_connector_mappings(rotkehlchen_api_server)
    assert len(result['entries']) == result['entries_found'] == result['entries_total'] == NUM_PACKAGED_ASSETS_MAPPINGS  # noqa: E501

    # query all common mappings
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={'connector': None},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found']
    assert result['entries_found'] > 300

    # query all kraken mappings
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={'connector': 'kraken'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found']
    assert result['entries_found'] > 300

    # query by symbol all the kraken mappings
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={'connector_symbol': 'eth', 'connector': 'kraken'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert all(entry['connector'] == 'kraken' for entry in result['entries'])
    assert {'XETH', 'ETHW', 'WETH', 'ETH2'}.issubset(
        {entry['connector_symbol'] for entry in result['entries']},
    )


def test_connector_asset_mappings_add(rotkehlchen_api_server: APIServer) -> None:
    """Test the connector asset mappings API for adding the mappings."""
    all_mappings = _get_all_connector_mappings(rotkehlchen_api_server)['entries']
    added_mappings = [{
        'asset': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'connector_symbol': 'NEW1',
        'connector': 'binance',
    }, {
        'asset': 'eip155:1/erc20:0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF',
        'connector_symbol': 'NEW2',
        'connector': 'kraken',
    }]

    # add two new mappings
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'entries': added_mappings,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result is True

    # check that the mappings were indeed added
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'offset': 0,
            'limit': 4000,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    all_mappings_after_addition = result['entries']
    assert len(all_mappings_after_addition) == result['entries_found'] == NUM_PACKAGED_ASSETS_MAPPINGS + 2  # noqa: E501
    for new_mapping in added_mappings:
        assert new_mapping not in all_mappings
        assert new_mapping in all_mappings_after_addition


def test_connector_asset_mappings_update(rotkehlchen_api_server: APIServer) -> None:
    """Test the connector asset mappings API for updating the mappings."""
    all_mappings = _get_all_connector_mappings(rotkehlchen_api_server)['entries']

    # updated a mapping of asset NEW1
    initial_mapping = all_mappings[0]
    updated_mapping = {
        'asset': 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
        'connector_symbol': all_mappings[0]['connector_symbol'],
        'connector': all_mappings[0]['connector'],
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={'entries': [updated_mapping]},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result is True

    # check if the mappings is updated
    all_mappings_after_update = _get_all_connector_mappings(rotkehlchen_api_server)['entries']
    assert all_mappings_after_update[0] == updated_mapping
    assert initial_mapping in all_mappings and initial_mapping not in all_mappings_after_update
    assert updated_mapping not in all_mappings and updated_mapping in all_mappings_after_update


def test_connector_asset_mappings_delete(rotkehlchen_api_server: APIServer) -> None:
    """Test the connector asset mappings API for deleting the mappings."""
    all_mappings = _get_all_connector_mappings(rotkehlchen_api_server)['entries']

    # delete the mapping of NEW2
    deleted_mapping = {
        'connector_symbol': all_mappings[0]['connector_symbol'],
        'connector': all_mappings[0]['connector'],
    }
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'entries': [deleted_mapping],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result is True

    result = _get_all_connector_mappings(rotkehlchen_api_server)
    all_mappings_after_deletion = result['entries']
    assert len(all_mappings_after_deletion) == result['entries_found'] == NUM_PACKAGED_ASSETS_MAPPINGS - 1  # noqa: E501
    assert all_mappings[0] not in all_mappings_after_deletion


def test_connector_asset_mappings_pagination(rotkehlchen_api_server: APIServer) -> None:
    """Test pagination in connector asset mappings APIs."""
    all_mappings = _get_all_connector_mappings(rotkehlchen_api_server)['entries']

    # pagination limit works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'offset': 0,
            'limit': 1,
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    assert result['entries'] == [all_mappings[0]]
    assert result['entries_found'] == NUM_PACKAGED_ASSETS_MAPPINGS

    # pagination offset works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'offset': 1,
            'limit': 1,
        },
    )
    result = assert_proper_sync_response_with_result(response=response)
    assert result['entries'] == [all_mappings[1]]
    assert result['entries_found'] == NUM_PACKAGED_ASSETS_MAPPINGS


def test_connector_asset_mappings_errors(rotkehlchen_api_server: APIServer) -> None:
    """Test the conflict errors in connector asset mappings APIs."""
    # add a mapping that already exists and expect failure
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b',
                'connector': None,
                'connector_symbol': 'AXS',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to add the connector asset mapping AXS in None because it already exists in the DB.'  # noqa: E501
        ),
    )

    # check that some connectors are not allowed since they share mappings with another one.
    for location, replacement_location in (
        (LOCATION_BINANCEUS, LOCATION_BINANCE),
        (LOCATION_COINBASEPRIME, LOCATION_COINBASE),
        (LOCATION_COINBASEPRO, LOCATION_COINBASE),
    ):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'connectorassetmappingsresource'),
            json={'entries': [
                {'asset': 'BTC', 'connector': location, 'connector_symbol': 'XYZ'},
            ]},
        )
        assert_error_response(
            response=response,
            status_code=HTTPStatus.BAD_REQUEST,
            contained_in_msg=f'Mappings for {location} should use the {replacement_location} connector.',  # noqa: E501
        )

    # delete a mapping that does not exist and expect failure
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'entries': [{
                'connector_symbol': 'DNE',
                'connector': 'kraken',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to delete the connector asset mapping DNE in kraken because it does not exist in the DB.'  # noqa: E501
        ),
    )

    # update a mapping that does not exist and expect failure
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'connectorassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
                'connector_symbol': 'DNE',
                'connector': 'kraken',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to update the connector asset mapping DNE in kraken because it does not exist in the DB.'  # noqa: E501
        ),
    )
