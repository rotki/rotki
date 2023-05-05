from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

import requests

from rotkehlchen.assets.asset import CustomAsset
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.checks import assert_asset_result_order

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

TEST_CUSTOM_ASSETS = [
    CustomAsset.initialize(
        identifier=str(uuid4()),
        name='Gold Bar',
        custom_asset_type='inheritance',
    ),
    CustomAsset.initialize(
        identifier=str(uuid4()),
        name='House',
        notes='A 4bd detached bungalow',
        custom_asset_type='real estate',
    ),
    CustomAsset.initialize(
        identifier=str(uuid4()),
        name='Land',
        custom_asset_type='real estate',
    ),
    CustomAsset.initialize(
        identifier=str(uuid4()),
        name='Netflix',
        custom_asset_type='stocks',
    ),
]


def _populate_custom_assets_table(db_handler: 'DBHandler'):
    db_custom_assets = DBCustomAssets(db_handler)
    for entry in TEST_CUSTOM_ASSETS:
        db_custom_assets.add_custom_asset(entry)


def test_get_custom_assets(rotkehlchen_api_server) -> None:
    _populate_custom_assets_table(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert result['entries_found'] == len(TEST_CUSTOM_ASSETS)
    assert result['entries'] == [entry.to_dict() for entry in TEST_CUSTOM_ASSETS]

    # test that filtering works as expected
    # filter by name
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'goLD'},  # also check that case doesn't matter
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 1
    assert result['entries'][0] == TEST_CUSTOM_ASSETS[0].to_dict()

    # filter by custom asset type
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'custom_asset_type': 'ReAl EsTaTe'},  # also check that case doesn't matter
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 2
    assert result['entries_found'] == 2
    assert result['entries'] == [entry.to_dict() for entry in TEST_CUSTOM_ASSETS[1:3]]

    # filter by identifier
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'identifier': TEST_CUSTOM_ASSETS[3].identifier},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries_found'] == 1
    assert result['entries'][0] == TEST_CUSTOM_ASSETS[3].to_dict()

    # test that filtering with a non-existent name returns no entries
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'idontexist'},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 0

    # sort by custom asset type
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={
            'order_by_attributes': ['custom_asset_type'],
            'ascending': [True],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 4
    assert_asset_result_order(
        data=result['entries'],
        is_ascending=True,
        order_field='custom_asset_type',
    )

    # sort by name
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={
            'order_by_attributes': ['name'],
            'ascending': [True],
        },
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 4
    assert_asset_result_order(
        data=result['entries'],
        is_ascending=True,
        order_field='name',
    )


def test_add_custom_asset(rotkehlchen_api_server) -> None:
    data = {'name': 'XYZ', 'custom_asset_type': 'stocks'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    assert_proper_response(response)
    # check the custom asset is present in the db
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0]['name'] == data['name']
    assert result['entries'][0]['custom_asset_type'] == data['custom_asset_type']

    # test that adding custom asset without the required fields fails
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'XYZ'},
    )
    assert_error_response(
        response,
        contained_in_msg='"Missing data for required field.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # test that adding an already existing custom asset fails
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'XYZ', 'custom_asset_type': 'stocks'},
    )
    assert_error_response(
        response,
        contained_in_msg='Custom asset with name "XYZ" and type "stocks" already present in the database',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )


def test_edit_custom_asset(rotkehlchen_api_server) -> None:
    _populate_custom_assets_table(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    data = TEST_CUSTOM_ASSETS[0].to_dict()
    data['name'] = 'Milky Way'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    assert_proper_response(response)

    # check that the asset was indeed updated
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'Milky Way'},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0] == data

    # check that using an already existing name and type fails
    data['name'] = 'Land'
    data['custom_asset_type'] = 'real estate'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    assert_error_response(
        response,
        contained_in_msg='already present in the database',
        status_code=HTTPStatus.CONFLICT,
    )

    # check that editing a non-existent custom asset fails
    data['identifier'] = str(uuid4())
    data['name'] = 'Lamborghini'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    assert_error_response(response, contained_in_msg='but it was not found', status_code=HTTPStatus.CONFLICT)  # noqa: E501

    # check that keeping the name unchanged works
    data = TEST_CUSTOM_ASSETS[2].to_dict()
    data['notes'] = 'Unchanged LFG!'
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json=data,
    )
    assert_proper_response(response)

    # check that the custom asset is still present and only the notes changed
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'name': 'Land'},
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 1
    assert result['entries'][0] == data


def test_delete_custom_asset(rotkehlchen_api_server) -> None:
    _populate_custom_assets_table(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'identifier': TEST_CUSTOM_ASSETS[0].identifier},
    )
    assert_proper_response(response)

    # check that the number of custom assets have reduced
    # and the deleted custom asset is no longer present
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert len(result['entries']) == 3
    assert TEST_CUSTOM_ASSETS[0].identifier not in [entry['identifier'] for entry in result['entries']]  # noqa: E501
    assert TEST_CUSTOM_ASSETS[0].name not in [entry['name'] for entry in result['entries']]

    # check that deleting a non-existent custom asset fails
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'customassetsresource',
        ),
        json={'identifier': str(uuid4())},
    )
    assert_error_response(
        response,
        contained_in_msg='but it was not found in the DB',
        status_code=HTTPStatus.CONFLICT,
    )


def test_custom_asset_types(rotkehlchen_api_server) -> None:
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'customassetstypesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 0

    # add custom assets
    _populate_custom_assets_table(rotkehlchen_api_server.rest_api.rotkehlchen.data.db)
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'customassetstypesresource',
        ),
    )
    result = assert_proper_response_with_result(response)
    assert len(result) == 3
    assert result == ['inheritance', 'real estate', 'stocks']
