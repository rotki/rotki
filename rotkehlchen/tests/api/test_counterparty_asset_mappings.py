from http import HTTPStatus
from typing import TYPE_CHECKING, Any, Final

import pytest
import requests

from rotkehlchen.db.filtering import CounterpartyAssetMappingsFilterQuery
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.globaldb.handler import GlobalDBHandler

NUM_PACKAGED_COUNTERPARTY_ASSETS_MAPPINGS: Final = 31


def _get_all_counterparty_mappings(globaldb: 'GlobalDBHandler') -> dict[str, Any]:
    """Utility function to return all the counterparty asset mappings in the DB."""
    mappings, mappings_found, mappings_total = globaldb.query_asset_mappings_by_type(
        mapping_type='counterparty',
        filter_query=CounterpartyAssetMappingsFilterQuery.make(offset=0, limit=5000),
        dict_keys=('asset', 'counterparty', 'counterparty_symbol'),
        query_columns='local_id, counterparty, symbol',
        location_or_counterparty_reader_callback=lambda x: x,
    )
    return {
        'entries': mappings,
        'entries_found': mappings_found,
        'entries_total': mappings_total,
    }


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparty_asset_mappings_query(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    result = _get_all_counterparty_mappings(globaldb)  # query all the mappings
    assert len(result['entries']) == result['entries_found'] == result['entries_total'] == NUM_PACKAGED_COUNTERPARTY_ASSETS_MAPPINGS  # noqa: E501

    response = requests.post(  # query all common mappings
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'counterparty': None},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == NUM_PACKAGED_COUNTERPARTY_ASSETS_MAPPINGS  # noqa: E501

    response = requests.post(  # query all hyperliquid mappings
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'counterparty': 'hyperliquid'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == result['entries_found'] == NUM_PACKAGED_COUNTERPARTY_ASSETS_MAPPINGS  # noqa: E501

    response = requests.post(  # query by symbol all the hyperliquid mappings
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'counterparty_symbol': 'HYPE', 'counterparty': 'hyperliquid'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert all(entry['counterparty'] == 'hyperliquid' for entry in result['entries'])


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparty_asset_mappings_add(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    all_mappings = _get_all_counterparty_mappings(globaldb)['entries']
    added_mappings = [{
        'asset': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
        'counterparty_symbol': 'NEW1',
        'counterparty': 'hyperliquid',
    }, {
        'asset': 'eip155:1/erc20:0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF',
        'counterparty_symbol': 'NEW2',
        'counterparty': 'hyperliquid',
    }]

    response = requests.put(  # add two new mappings
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'entries': added_mappings},
    )
    assert assert_proper_sync_response_with_result(response)

    response = requests.post(  # check that the mappings were indeed added
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'offset': 0, 'limit': 4000},
    )
    result = assert_proper_sync_response_with_result(response)
    all_mappings_after_addition = result['entries']
    assert len(all_mappings_after_addition) == result['entries_found'] == NUM_PACKAGED_COUNTERPARTY_ASSETS_MAPPINGS + 2  # noqa: E501
    for new_mapping in added_mappings:
        assert new_mapping not in all_mappings
        assert new_mapping in all_mappings_after_addition


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparty_asset_mappings_update(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
                'counterparty_symbol': 'NEW1',
                'counterparty': 'hyperliquid',
            }],
        },
    ))
    all_mappings = _get_all_counterparty_mappings(globaldb)['entries']
    initial_mapping = all_mappings[0]
    updated_mapping = {  # updated a mapping of asset NEW1
        'asset': 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
        'counterparty_symbol': all_mappings[0]['counterparty_symbol'],
        'counterparty': all_mappings[0]['counterparty'],
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'entries': [updated_mapping]},
    )
    assert assert_proper_sync_response_with_result(response)

    # check if the mappings is updated
    all_mappings_after_update = _get_all_counterparty_mappings(globaldb)['entries']
    assert all_mappings_after_update[0] == updated_mapping
    assert initial_mapping in all_mappings and initial_mapping not in all_mappings_after_update
    assert updated_mapping not in all_mappings and updated_mapping in all_mappings_after_update


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparty_asset_mappings_delete(
        rotkehlchen_api_server: 'APIServer',
        globaldb: 'GlobalDBHandler',
) -> None:
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
                'counterparty_symbol': 'NEW1',
                'counterparty': 'hyperliquid',
            }],
        },
    ))
    all_mappings = _get_all_counterparty_mappings(globaldb)['entries']

    deleted_mapping = {  # delete the mapping of NEW1
        'counterparty_symbol': all_mappings[0]['counterparty_symbol'],
        'counterparty': all_mappings[0]['counterparty'],
    }
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={'entries': [deleted_mapping]},
    )
    assert assert_proper_sync_response_with_result(response)

    result = _get_all_counterparty_mappings(globaldb)
    assert all_mappings[0] not in result['entries']


@pytest.mark.parametrize('have_decoders', [True])
def test_counterparty_asset_mappings_errors(rotkehlchen_api_server: 'APIServer') -> None:
    assert_proper_sync_response_with_result(requests.put(
        api_url_for(    # add a mapping that already exists and expect failure
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b',
                'counterparty': 'hyperliquid',
                'counterparty_symbol': 'AXS',
            }],
        },
    ))
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0xBB0E17EF65F82Ab018d8EDd776e8DD940327B28b',
                'counterparty': 'hyperliquid',
                'counterparty_symbol': 'AXS',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to add the counterparty asset mapping of AXS in hyperliquid because it already exists in the DB.'  # noqa: E501
        ),
    )

    response = requests.delete(
        api_url_for(  # delete a mapping that does not exist and expect failure
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'counterparty_symbol': 'DNE',
                'counterparty': 'hyperliquid',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to delete the counterparty asset mapping of DNE in hyperliquid because it does not exist in the DB.'  # noqa: E501
        ),
    )

    response = requests.patch(
        api_url_for(  # update a mapping that does not exist and expect failure
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
                'counterparty_symbol': 'DNE',
                'counterparty': 'hyperliquid',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg=(
            'Failed to update the counterparty asset mapping of DNE in hyperliquid because it does not exist in the DB.'  # noqa: E501
        ),
    )

    response = requests.put(
        api_url_for(  # adding a mapping for a counterparty that is not supported should fail
            rotkehlchen_api_server,
            'counterpartyassetmappingsresource',
        ),
        json={
            'entries': [{
                'asset': 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
                'counterparty_symbol': 'DNE',
                'counterparty': 'hyper',
            }],
        },
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Unknown counterparty hyper provided',
    )
