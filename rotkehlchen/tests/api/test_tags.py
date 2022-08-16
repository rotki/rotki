from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_error_response, assert_proper_response
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2
from rotkehlchen.tests.utils.rotkehlchen import setup_balances


def test_add_and_query_tags(
        rotkehlchen_api_server,
):
    """Test that adding and querying tags via the API works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2

    # And finally also check the DB to be certain
    with rotki.data.db.conn.read_ctx() as cursor:
        db_response = rotki.data.db.get_tags(cursor)
    assert len(db_response) == 2
    assert db_response['Public'].serialize() == tag1
    assert db_response['private'].serialize() == tag2


def test_add_tag_without_description(
        rotkehlchen_api_server,
):
    """Test that adding a tag without a description works"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    tag1 = {
        'name': 'Public',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
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
            rotkehlchen_api_server,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['Public'] == tag1

    # And finally also check the DB to be certain
    with rotki.data.db.conn.read_ctx() as cursor:
        db_response = rotki.data.db.get_tags(cursor)
    assert len(db_response) == 1
    assert db_response['Public'].serialize() == tag1


@pytest.mark.parametrize('verb', ('PUT', 'PATCH'))
def test_add_edit_tag_errors(
        rotkehlchen_api_server,
        verb,
):
    """Test that errors in input data while adding/editing a tag are handled correctly"""
    # Name missing
    tag = {
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag,
    )
    assert_error_response(
        response=response,
        contained_in_msg='name": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Invalid type for name
    tag = {
        'name': 456,
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag,
    )
    assert_error_response(
        response=response,
        contained_in_msg='name": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Invalid type for description
    tag = {
        'name': 'Public',
        'description': 54.2,
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.request(
        verb,
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag,
    )
    assert_error_response(
        response=response,
        contained_in_msg='description": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    model_tag = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    for field in ('background_color', 'foreground_color'):

        if verb == 'PUT':
            # Missing color
            tag = model_tag.copy()
            tag.pop(field)
            response = requests.request(
                verb,
                api_url_for(
                    rotkehlchen_api_server,
                    "tagsresource",
                ), json=tag,
            )
            assert_error_response(
                response=response,
                contained_in_msg='Background and foreground color should be given for the tag',
                status_code=HTTPStatus.BAD_REQUEST,
            )
        # Invalid color type
        tag = model_tag.copy()
        tag[field] = 55
        response = requests.request(
            verb,
            api_url_for(
                rotkehlchen_api_server,
                "tagsresource",
            ), json=tag,
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'"{field}": ["Failed to deserialize color code from int',
            status_code=HTTPStatus.BAD_REQUEST,
        )
        # Wrong kind of string
        tag = model_tag.copy()
        tag[field] = 'went'
        response = requests.request(
            verb,
            api_url_for(
                rotkehlchen_api_server,
                "tagsresource",
            ), json=tag,
        )
        assert_error_response(
            response=response,
            contained_in_msg=(
                f'"{field}": ["The given color code value \\"went\\" could '
                f'not be processed as a hex color value'
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
        # Hex code but out of range
        tag = model_tag.copy()
        tag[field] = 'ffef01ff'
        response = requests.request(
            verb,
            api_url_for(
                rotkehlchen_api_server,
                "tagsresource",
            ), json=tag,
        )
        assert_error_response(
            response=response,
            contained_in_msg=(
                f'"{field}": ["The given color code value \\"ffef01ff\\" is out '
                f'of range for a normal color field'
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )
        # Hex code but not enough digits
        tag = model_tag.copy()
        tag[field] = 'ff'
        response = requests.request(
            verb,
            api_url_for(
                rotkehlchen_api_server,
                "tagsresource",
            ), json=tag,
        )
        assert_error_response(
            response=response,
            contained_in_msg=(
                f'"{field}": ["The given color code value \\"ff\\" does not '
                f'have 6 hexadecimal digits'
            ),
            status_code=HTTPStatus.BAD_REQUEST,
        )


def test_edit_tags(
        rotkehlchen_api_server,
):
    """Test that editing a tag via the REST API works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add two tags
    tag1 = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'private',
        'description': 'My private accounts',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag2,
    )
    assert_proper_response(response)

    # Now try to edit the second tag and change all its fields
    edit_tag_data = {
        'name': 'PrIvAtE',  # notice that name should match case insensitive
        'description': 'My super private accounts',
        'background_color': '010101',
        'foreground_color': 'fefefe',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    tag2 = edit_tag_data
    tag2['name'] = 'private'
    assert data['result']['private'] == tag2

    # Now try to edit the second tag and change all but description
    edit_tag_data = {
        'name': 'private',
        'background_color': '020202',
        'foreground_color': 'fafafa',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    edit_tag_data['description'] = tag2['description']
    assert data['result']['private'] == edit_tag_data
    tag2 = data['result']['private']

    # Now try to edit the second tag and change only foreground_color
    edit_tag_data = {
        'name': 'private',
        'foreground_color': 'fbfbfb',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    tag2['foreground_color'] = edit_tag_data['foreground_color']
    assert data['result']['private'] == tag2
    tag2 = data['result']['private']

    # Now try to edit the second tag and change only background_color
    edit_tag_data = {
        'name': 'private',
        'background_color': '000000',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    tag2['background_color'] = edit_tag_data['background_color']
    assert data['result']['private'] == tag2

    # Now try to edit a tag without modifying any field and see it's an error
    edit_tag_data = {'name': 'private'}
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='No field was given to edit for tag "private"',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Now try to edit a non-existing tag
    edit_tag_data = {
        'name': 'hello',
        'background_color': '000000',
    }
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=edit_tag_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to edit tag with name "hello" which does not exist',
        status_code=HTTPStatus.CONFLICT,
    )

    # Query tags and see that both added/edited tags are in the response
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2

    # And finally also check the DB to be certain
    with rotki.data.db.conn.read_ctx() as cursor:
        db_response = rotki.data.db.get_tags(cursor)
    assert len(db_response) == 2
    assert db_response['Public'].serialize() == tag1
    assert db_response['private'].serialize() == tag2


def test_delete_tags(
        rotkehlchen_api_server,
):
    """Test that deleting a tag via the REST API works fine"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add two tags
    tag1 = {
        'name': 'Public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'private',
        'description': 'My private accounts',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=tag2,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2
    # Query tags and see that both added tags are in the response
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 2
    assert data['result']['Public'] == tag1
    assert data['result']['private'] == tag2

    # Now delete the first tag
    delete_tag_data = {
        'name': 'pUbLiC',  # notice that name should match case insensitive
    }
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=delete_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1

    # Now try to delete a non existing tag
    delete_tag_data = {'name': 'hello'}
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=delete_tag_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Tried to delete tag with name "hello" which does not exist',
        status_code=HTTPStatus.CONFLICT,
    )

    # Query tags and see that the deleted tag is not in the response
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ),
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['private'] == tag2

    # And finally also check the DB to be certain
    with rotki.data.db.conn.read_ctx() as cursor:
        db_response = rotki.data.db.get_tags(cursor)
    assert len(db_response) == 1
    assert db_response['private'].serialize() == tag2


def test_delete_tag_errors(
        rotkehlchen_api_server,
):
    """Test that errors in input data while deleting a tag are handled correctly"""
    # Name missing
    data = {}
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='name": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )
    # Invalid type for name
    data = {'name': 55.52}
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='name": ["Not a valid string',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_delete_utilized_tag(rotkehlchen_api_server):
    """
    Test that deleting a tag that is already utilized by an account
    also removes it from the account"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Add two tags
    tag1 = {
        'name': 'public',
        'description': 'My public accounts',
        'background_color': 'ffffff',
        'foreground_color': '000000',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag1,
    )
    assert_proper_response(response)
    tag2 = {
        'name': 'desktop',
        'description': 'Accounts that are stored in the desktop PC',
        'background_color': '000000',
        'foreground_color': 'ffffff',
    }
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'tagsresource',
        ), json=tag2,
    )
    assert_proper_response(response)

    # Now add 2 accounts both of them using the above tags
    new_btc_accounts = [UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]
    btc_balances = ['10000', '500500000']
    setup = setup_balances(
        rotki,
        ethereum_accounts=None,
        btc_accounts=new_btc_accounts,
        eth_balances=None,
        token_balances=None,
        btc_balances=btc_balances,
    )
    accounts_data = [{
        "address": new_btc_accounts[0],
        "label": 'my btc miner',
        'tags': ['public', 'desktop'],
    }, {
        "address": new_btc_accounts[1],
        'label': 'other account',
        'tags': ['desktop'],
    }]
    with setup.bitcoin_patch:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            "blockchainsaccountsresource",
            blockchain='BTC',
        ), json={'accounts': accounts_data})
    assert_proper_response(response)

    # Now delete the tag used by both accounts
    delete_tag_data = {
        'name': 'desktop',
    }
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            "tagsresource",
        ), json=delete_tag_data,
    )
    assert_proper_response(response)
    data = response.json()
    assert len(data['result']) == 1
    assert data['result']['public'] is not None

    # Now check the DB directly and see that tag mappings of the deleted tag are gone
    cursor = rotki.data.db.conn.cursor()
    query = cursor.execute('SELECT object_reference, tag_name FROM tag_mappings;').fetchall()
    assert len(query) == 1
    assert query[0][0] == UNIT_BTC_ADDRESS1
    assert query[0][1] == 'public'
