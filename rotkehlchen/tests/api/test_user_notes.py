from http import HTTPStatus

import pytest
import requests

from rotkehlchen.constants.limits import FREE_USER_NOTES_LIMIT
from rotkehlchen.db.filtering import UserNotesFilterQuery
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_random_user_notes, make_user_notes_entries


def test_add_get_user_notes(rotkehlchen_api_server):
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#1',
            'content': 'Romero Uno',
            'location': 'manual balances',
            'is_pinned': True,
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 1

    # try adding more user notes
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#2',
            'content': 'ETH/MOON TP@GOBLIN',
            'location': 'ledger actions',
            'is_pinned': False,
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 2
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'title': '#3',
            'content': 'Let us try a new approach',
            'location': 'trades',
            'is_pinned': True,
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result == 3

    # check that a total of user notes are in the db.
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert len(result['entries']) == 3

    # check that filtering by title substring works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={'title_substring': '3'},
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result['entries_found'] == 1
    assert len(result['entries']) == 1

    # check that filtering by location works
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={'location': 'trades'},
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result['entries_found'] == 1
    assert result['entries_total'] == 3
    assert result['entries'][0]['location'] == 'trades'

    # test sorting by multiple fields
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'order_by_attributes': ['is_pinned', 'last_update_timestamp'],
            'ascending': [False, True],
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert len(result['entries']) == 3
    assert result['entries'][0]['title'] == '#1'
    assert result['entries'][1]['title'] == '#3'
    assert result['entries'][2]['title'] == '#2'


def test_edit_user_notes(rotkehlchen_api_server):
    generated_entries = make_user_notes_entries()
    for entry in generated_entries:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_user_note(
            title=entry['title'],
            content=entry['content'],
            location=entry['location'],
            is_pinned=entry['is_pinned'],
            has_premium=True,
        )

    # check that editing a user note works as expected.
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
            'title': 'My TODO List',
            'content': 'Dont sleep, wake up!!!!!',
            'location': 'ledger actions',
            'last_update_timestamp': 12345678,
            'is_pinned': True,
        },
    )
    assert_simple_ok_response(response)
    # confirm that the note was actually edited in the db
    filter_query = UserNotesFilterQuery.make()
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    with db.conn.read_ctx() as cursor:
        user_notes, _ = db.get_user_notes_and_limit_info(
            filter_query=filter_query,
            cursor=cursor,
            has_premium=True,
        )
    for note in user_notes:
        if note.identifier == 1:
            assert note.title == 'My TODO List'
            assert note.content == 'Dont sleep, wake up!!!!!'
            assert note.is_pinned is True
            assert note.last_update_timestamp > 12345678

    # check that editing a user note with an invalid identifier fails
    response = requests.patch(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 10,
            'title': 'INVALID 101',
            'content': 'Dont sleep, wake up!!!!!',
            'location': 'manual balances',
            'last_update_timestamp': 12345678,
            'is_pinned': False,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='User note with identifier 10 does not exist',
        status_code=HTTPStatus.CONFLICT,
    )


def test_delete_user_notes(rotkehlchen_api_server):
    generated_entries = make_user_notes_entries()
    for entry in generated_entries:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_user_note(
            title=entry['title'],
            content=entry['content'],
            location=entry['location'],
            is_pinned=entry['is_pinned'],
            has_premium=True,
        )

    # check that deleting a user note works as expected
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
        },
    )
    assert_proper_response(response, status_code=HTTPStatus.OK)

    # check that the user notes count reduced in db
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)
    assert result['entries_found'] == 2

    # check that deleting a user note that is deleted already fails.
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ), json={
            'identifier': 1,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='User note with identifier 1 not found in database',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_premium_limits(rotkehlchen_api_server, start_with_valid_premium):
    """Test that premium limits are set correctly"""
    generated_entries = make_random_user_notes(20)
    for entry in generated_entries:
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.add_user_note(
            title=entry['title'],
            content=entry['content'],
            location=entry['location'],
            is_pinned=entry['is_pinned'],
            has_premium=True,
        )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'usernotesresource',
        ),
        json={
            'order_by_attributes': ['is_pinned', 'last_update_timestamp'],
            'ascending': [False, True],
        },
    )
    result = assert_proper_response_with_result(response, status_code=HTTPStatus.OK)

    if start_with_valid_premium is False:
        assert result['entries_limit'] == FREE_USER_NOTES_LIMIT
        assert len(result['entries']) == FREE_USER_NOTES_LIMIT
        assert result['entries_total'] == 20
        assert result['entries_found'] == 20
        # Try to add a new entry and check that it fails
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'usernotesresource',
            ),
            json={
                'title': '#21',
                'content': 'I should fail',
                'location': 'trades',
                'is_pinned': True,
            },
        )
        assert_error_response(
            response=response,
            contained_in_msg=f'The limit of {FREE_USER_NOTES_LIMIT} user notes has been',
            status_code=HTTPStatus.CONFLICT,
        )
    else:
        assert result['entries_limit'] == -1
        assert len(result['entries']) == 20
        assert result['entries_total'] == 20
        assert result['entries_found'] == 20
