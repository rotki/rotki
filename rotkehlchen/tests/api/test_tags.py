from http import HTTPStatus

import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response


def test_add_and_query_tags(
        rotkehlchen_api_server_with_exchanges,
):
    """Test that adding and querying tags via the API works fine"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert data['result'] == {}, 'In the beginning we should have no tags'

    # Add one tag and see its response shows it was added
    tag1 = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ), json=tag1,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['Public'] == tag1

    # Add a second tag and see its response shows it was added
    tag2 = {
        'name': 'private',
        'description': 'My private accounts',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ), json=tag2,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2

    # Try to add a different tag that matches tag1 case insensitive and see request fails
    tag3 = {
        'name': 'PuBlIc',
        'description': 'Some other tag',
        'background_color': 'f2f2f2',
        'foreground_color': '222222',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ), json=tag3,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tag with name PuBlIc already exists.',
        status_code=HTTPStatus.CONFLICT,
    )

    # Query tags and see that both added tags are in the response
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2

    # And finally also check the DB to be certain
    db_response = rotki.data.db.get_tags()
    assert len(db_response) == 2
    assert db_response['Public'].serialize() == tag1
    assert db_response['private'].serialize() == tag2


def test_add_tag_without_description(
        rotkehlchen_api_server_with_exchanges,
):
    """Test that adding a tag without a description works"""
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    tag1 = {
        'name': 'Public',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ), json=tag1,
    )
    assert_proper_response(response)
    tag1['description'] = None
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['Public'] == tag1

    # Query tags and see that the added tag is there
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['Public'] == tag1

    # And finally also check the DB to be certain
    db_response = rotki.data.db.get_tags()
    assert len(db_response) == 1
    assert db_response['Public'].serialize() == tag1
